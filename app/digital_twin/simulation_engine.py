"""
Digital Twin Simulation Engine.

This module is intentionally framework-agnostic (no Flask/DB imports) so it
can be unit-tested on its own and reused for the "compare all recommended
crops" feature (which runs several headless simulations back to back).

The engine operates on a plain dict "state" object so it can be stored as
JSON in a database column (see DigitalTwinSession.state_json in models.py).
"""

import random
from app.digital_twin.crop_config import (
    get_crop_config, get_stage_for_day, get_maturity_percent
)

WEATHER_OPTIONS = ["Sunny", "Cloudy", "Light Rain", "Heavy Rain", "Drought", "Heat Wave"]


def new_state(crop_name, farm_data=None):
    """Create the initial Digital Twin state for a freshly selected crop."""
    farm_data = farm_data or {}
    cfg = get_crop_config(crop_name)

    state = {
        "crop": crop_name.lower(),
        "cropDisplayName": cfg["display_name"],
        "simulationDay": 0,
        "durationDays": cfg["duration_days"],
        "growthStage": get_stage_for_day(crop_name, 0),
        "maturityPercent": 0.0,
        "cropHealth": 90.0,
        "soilMoisture": float(farm_data.get("soilMoisture", 55)),
        "nitrogen": float(farm_data.get("nitrogen", cfg["ideal_npk"]["n"] * 0.7)),
        "phosphorus": float(farm_data.get("phosphorus", cfg["ideal_npk"]["p"] * 0.7)),
        "potassium": float(farm_data.get("potassium", cfg["ideal_npk"]["k"] * 0.7)),
        "temperature": float(farm_data.get("temperature", 28)),
        "humidity": float(farm_data.get("humidity", 65)),
        "rainfall": float(farm_data.get("rainfall", 100)),
        "ph": float(farm_data.get("ph", 6.5)),
        "irrigation": float(farm_data.get("irrigation", 0)),
        "weather": "Sunny",
        "pestLevel": 0.0,
        "diseaseLevel": 0.0,
        "waterUsedLitres": 0.0,
        "fertilizerAppliedKg": 0.0,
        "pesticideAppliedL": 0.0,
        "acreage": float(farm_data.get("acreage", 1)),
        "expectedYieldKg": cfg["base_yield_per_acre_kg"] * float(farm_data.get("acreage", 1)),
        "actualYieldKg": None,
        "status": "growing",  # growing | harvested | failed
        "eventsLog": [],
        "actionsLog": [],
        "alerts": [],
        "availableActions": [],
    }
    _recalculate(state)
    return state


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _weighted_health(state, cfg):
    """Composite health score from water, nutrients, weather, pest, disease."""
    lo, hi = cfg["ideal_moisture"]
    moisture = state["soilMoisture"]
    if lo <= moisture <= hi:
        water_score = 100
    else:
        dist = (lo - moisture) if moisture < lo else (moisture - hi)
        water_score = _clamp(100 - dist * 2)

    npk_ideal = cfg["ideal_npk"]
    npk_scores = []
    for key, ideal_key in (("nitrogen", "n"), ("phosphorus", "p"), ("potassium", "k")):
        ideal = npk_ideal[ideal_key]
        actual = state[key]
        dist = abs(ideal - actual)
        npk_scores.append(_clamp(100 - dist * 1.2))
    nutrient_score = sum(npk_scores) / len(npk_scores)

    t_lo, t_hi = cfg["temp_ideal_range"]
    temp = state["temperature"]
    if t_lo <= temp <= t_hi:
        temp_score = 100
    else:
        dist = (t_lo - temp) if temp < t_lo else (temp - t_hi)
        temp_score = _clamp(100 - dist * 3)

    ph_score = _clamp(100 - abs(state.get("ph", 6.5) - 6.5) * 22)
    humidity_score = _clamp(100 - abs(state.get("humidity", 65) - 65) * 1.4)

    pest_score = _clamp(100 - state["pestLevel"] * 1.1)
    disease_score = _clamp(100 - state["diseaseLevel"] * 1.3)

    health = (
        water_score * 0.25
        + nutrient_score * 0.23
        + temp_score * 0.14
        + ph_score * 0.09
        + humidity_score * 0.06
        + pest_score * 0.12
        + disease_score * 0.11
    )
    return round(_clamp(health), 1)


def apply_conditions(state, conditions):
    """Apply what-if input values without advancing the simulation day."""
    for key in ("temperature", "humidity", "rainfall", "ph", "nitrogen", "phosphorus", "potassium", "irrigation"):
        if key in conditions and conditions[key] not in (None, ""):
            state[key] = float(conditions[key])
    if "rainfall" in conditions or "irrigation" in conditions:
        state["soilMoisture"] = _clamp(state["soilMoisture"] + state.get("rainfall", 0) / 12 + state.get("irrigation", 0) / 8)
    _recalculate(state)
    return state


def _recalculate(state):
    """Refresh derived fields: stage, maturity, health, yield, alerts, actions."""
    cfg = get_crop_config(state["crop"])
    day = state["simulationDay"]

    state["growthStage"] = get_stage_for_day(state["crop"], day)
    state["maturityPercent"] = get_maturity_percent(state["crop"], day)
    state["cropHealth"] = _weighted_health(state, cfg)

    health_factor = state["cropHealth"] / 100.0
    base_total = cfg["base_yield_per_acre_kg"] * state["acreage"]
    state["expectedYieldKg"] = round(base_total * (0.4 + 0.6 * health_factor), 1)

    state["alerts"], state["availableActions"] = _build_alerts_and_actions(state, cfg)

    if state["cropHealth"] <= 15:
        state["status"] = "failed"


def _build_alerts_and_actions(state, cfg):
    alerts = []
    actions = ["apply_fertilizer", "apply_treatment"]  # always allowed baseline

    lo, hi = cfg["ideal_moisture"]
    moisture = state["soilMoisture"]
    if moisture < lo:
        alerts.append(f"Soil moisture is low ({moisture:.0f}%). Irrigation recommended.")
        actions.append("irrigate")
    elif moisture > cfg["waterlogging_risk_above"]:
        alerts.append(f"Soil moisture is very high ({moisture:.0f}%). Waterlogging risk.")
        actions.append("create_drainage")
    else:
        # moderate excess: irrigation still allowed but not urgent
        if moisture <= hi:
            actions.append("irrigate")

    if state["weather"] == "Heavy Rain":
        alerts.append("Heavy rain event: waterlogging and root damage risk rising.")
        if "create_drainage" not in actions:
            actions.append("create_drainage")
        actions.append("stop_irrigation")

    if state["weather"] == "Drought":
        alerts.append("Drought conditions: crop stress increasing.")
        if "irrigate" not in actions:
            actions.append("irrigate")

    npk_ideal = cfg["ideal_npk"]
    for key, ideal_key, label in (
        ("nitrogen", "n", "Nitrogen"),
        ("phosphorus", "p", "Phosphorus"),
        ("potassium", "k", "Potassium"),
    ):
        if state[key] < npk_ideal[ideal_key] * 0.6:
            alerts.append(f"{label} deficiency detected. Fertilizer application recommended.")

    if state["pestLevel"] > 30:
        alerts.append(f"Pest activity detected ({', '.join(cfg['pests'])}). Treatment recommended.")
    if state["diseaseLevel"] > 25:
        alerts.append(f"Disease risk detected ({', '.join(cfg['diseases'])}). Treatment recommended.")

    if state["maturityPercent"] >= cfg["maturity_harvest_window"][0]:
        alerts.append("Crop is approaching/at maturity. Ready for harvesting.")
        actions.append("harvest")

    # de-duplicate while preserving order
    seen = set()
    unique_actions = []
    for a in actions:
        if a not in seen:
            unique_actions.append(a)
            seen.add(a)

    return alerts, unique_actions


def advance_day(state, weather_override=None, rng=None):
    """Advance the simulation by exactly one day."""
    rng = rng or random
    cfg = get_crop_config(state["crop"])

    if state["status"] != "growing":
        return state

    state["simulationDay"] += 1
    day = state["simulationDay"]

    # --- Weather ---
    weather = weather_override or _roll_weather(rng)
    state["weather"] = weather
    if weather == "Heavy Rain":
        state["soilMoisture"] = _clamp(state["soilMoisture"] + rng.uniform(20, 35))
        state["temperature"] = _clamp(state["temperature"] - rng.uniform(1, 3), 10, 45)
        state["eventsLog"].append({"day": day, "event": "Heavy Rain"})
    elif weather == "Light Rain":
        state["soilMoisture"] = _clamp(state["soilMoisture"] + rng.uniform(5, 12))
    elif weather == "Drought":
        state["soilMoisture"] = _clamp(state["soilMoisture"] - rng.uniform(8, 15))
        state["eventsLog"].append({"day": day, "event": "Drought"})
    elif weather == "Heat Wave":
        state["temperature"] = _clamp(state["temperature"] + rng.uniform(3, 6), 10, 48)
        state["soilMoisture"] = _clamp(state["soilMoisture"] - rng.uniform(6, 10))
        state["eventsLog"].append({"day": day, "event": "Heat Wave"})
    else:
        state["temperature"] = _clamp(
            state["temperature"] + rng.uniform(-1.5, 1.5), 10, 45
        )

    # --- Natural moisture evapotranspiration ---
    evap = 3 + max(0, state["temperature"] - 28) * 0.4
    state["soilMoisture"] = _clamp(state["soilMoisture"] - evap)

    # --- Nutrient uptake by growing crop ---
    decay = cfg["npk_decay_per_day"]
    state["nitrogen"] = _clamp(state["nitrogen"] - decay["n"])
    state["phosphorus"] = _clamp(state["phosphorus"] - decay["p"])
    state["potassium"] = _clamp(state["potassium"] - decay["k"])

    # --- Pest / disease risk (higher when health is already low) ---
    stress_factor = 1.0 + (1.0 - state["cropHealth"] / 100.0)
    if rng.random() < cfg["pest_base_risk"] * stress_factor:
        state["pestLevel"] = _clamp(state["pestLevel"] + rng.uniform(15, 35))
        state["eventsLog"].append({"day": day, "event": "Pest activity detected"})
    else:
        state["pestLevel"] = _clamp(state["pestLevel"] - 2)

    if rng.random() < cfg["disease_base_risk"] * stress_factor:
        state["diseaseLevel"] = _clamp(state["diseaseLevel"] + rng.uniform(10, 25))
        state["eventsLog"].append({"day": day, "event": "Disease risk detected"})
    else:
        state["diseaseLevel"] = _clamp(state["diseaseLevel"] - 1.5)

    _recalculate(state)

    if state["simulationDay"] >= state["durationDays"] and state["status"] == "growing":
        state["alerts"].append("Crop has reached the end of its lifecycle. Please harvest.")

    return state


def _roll_weather(rng):
    weights = [0.45, 0.20, 0.15, 0.08, 0.07, 0.05]
    return rng.choices(WEATHER_OPTIONS, weights=weights, k=1)[0]


def perform_action(state, action, params=None):
    """Apply a farmer action to the state. Returns (state, message)."""
    params = params or {}
    cfg = get_crop_config(state["crop"])
    day = state["simulationDay"]
    message = ""

    if state["status"] != "growing":
        return state, "Simulation has ended; no further actions are possible."

    if action == "irrigate":
        litres = float(params.get("litres", 500)) * state["acreage"]
        gain = _clamp(15 + litres / 100.0, 0, 40)
        before = state["soilMoisture"]
        state["soilMoisture"] = _clamp(state["soilMoisture"] + gain)
        state["waterUsedLitres"] += litres
        state["actionsLog"].append({"day": day, "action": "Irrigate", "litres": litres})
        message = f"Irrigated the farm. Soil moisture {before:.0f}% -> {state['soilMoisture']:.0f}%."
        if state["soilMoisture"] > cfg["waterlogging_risk_above"]:
            message += " Warning: moisture is now high, watch for waterlogging."

    elif action == "apply_fertilizer":
        nutrient = params.get("nutrient", "nitrogen")
        amount = float(params.get("amount", 15))
        if nutrient not in ("nitrogen", "phosphorus", "potassium"):
            nutrient = "nitrogen"
        before = state[nutrient]
        state[nutrient] = _clamp(state[nutrient] + amount)
        state["fertilizerAppliedKg"] += amount * state["acreage"] * 0.5
        state["actionsLog"].append({"day": day, "action": f"Apply {nutrient} fertilizer", "amount": amount})
        message = f"Applied fertilizer. {nutrient.title()} {before:.0f}% -> {state[nutrient]:.0f}%."
        ideal = cfg["ideal_npk"]["n" if nutrient == "nitrogen" else ("p" if nutrient == "phosphorus" else "k")]
        if state[nutrient] > ideal * 1.4:
            message += " Warning: over-fertilization risk, nutrient imbalance may hurt the crop."

    elif action == "apply_treatment":
        before_pest = state["pestLevel"]
        before_disease = state["diseaseLevel"]
        state["pestLevel"] = _clamp(state["pestLevel"] - 45)
        state["diseaseLevel"] = _clamp(state["diseaseLevel"] - 35)
        state["pesticideAppliedL"] += 1.0 * state["acreage"]
        state["actionsLog"].append({"day": day, "action": "Apply treatment"})
        message = (
            f"Applied treatment. Pest {before_pest:.0f}% -> {state['pestLevel']:.0f}%, "
            f"Disease {before_disease:.0f}% -> {state['diseaseLevel']:.0f}%."
        )

    elif action == "create_drainage":
        before = state["soilMoisture"]
        state["soilMoisture"] = _clamp(state["soilMoisture"] - 25)
        state["actionsLog"].append({"day": day, "action": "Create drainage"})
        message = f"Drainage created. Soil moisture {before:.0f}% -> {state['soilMoisture']:.0f}%."

    elif action == "stop_irrigation":
        state["actionsLog"].append({"day": day, "action": "Stop irrigation"})
        message = "Irrigation paused until conditions improve."

    elif action == "harvest":
        return harvest(state)

    else:
        return state, f"Unknown action: {action}"

    _recalculate(state)
    return state, message


def harvest(state):
    cfg = get_crop_config(state["crop"])
    maturity = state["maturityPercent"]
    lo, hi = cfg["maturity_harvest_window"]

    if maturity < lo:
        timing_factor = 0.55 + 0.45 * (maturity / lo)
        timing_note = "Early harvest reduced the yield due to incomplete maturity."
    elif maturity > hi:
        overrun = min(maturity - hi, 20)
        timing_factor = max(0.6, 1 - overrun * 0.02)
        timing_note = "Late harvest slightly reduced yield quality."
    else:
        timing_factor = 1.0
        timing_note = "Harvested at optimal maturity."

    final_yield = round(state["expectedYieldKg"] * timing_factor, 1)
    state["actualYieldKg"] = final_yield
    state["status"] = "harvested"
    state["actionsLog"].append({"day": state["simulationDay"], "action": "Harvest"})

    message = (
        f"Harvest complete. Final yield: {final_yield} kg. {timing_note} "
        f"Final crop health: {state['cropHealth']:.0f}%."
    )
    return state, message


def run_headless_simulation(crop_name, farm_data, days=None, rng_seed=None):
    """
    Run a full simulation with no farmer interaction (auto-irrigate/fertilize
    when badly needed) purely to produce comparison numbers across crops.
    Used by the "Compare recommended crops" feature.
    """
    rng = random.Random(rng_seed)
    cfg = get_crop_config(crop_name)
    state = new_state(crop_name, farm_data)
    total_days = days or cfg["duration_days"]

    for _ in range(total_days):
        advance_day(state, rng=rng)
        # simple autopilot so the comparison isn't just "crop left to die"
        if "irrigate" in state["availableActions"] and state["soilMoisture"] < cfg["ideal_moisture"][0]:
            perform_action(state, "irrigate", {"litres": 600})
        if "create_drainage" in state["availableActions"]:
            perform_action(state, "create_drainage")
        if state["pestLevel"] > 40 or state["diseaseLevel"] > 35:
            perform_action(state, "apply_treatment")
        for nutrient in ("nitrogen", "phosphorus", "potassium"):
            ideal = cfg["ideal_npk"]["n" if nutrient == "nitrogen" else ("p" if nutrient == "phosphorus" else "k")]
            if state[nutrient] < ideal * 0.6:
                perform_action(state, "apply_fertilizer", {"nutrient": nutrient, "amount": 20})
        if state["status"] != "growing":
            break

    if state["status"] == "growing":
        harvest(state)

    risk = "High" if cfg["drought_sensitivity"] == "High" or cfg["heavy_rain_sensitivity"] == "High" else (
        "Medium" if "Medium" in (cfg["drought_sensitivity"], cfg["heavy_rain_sensitivity"]) else "Low"
    )

    return {
        "crop": cfg["display_name"],
        "expectedYieldKg": state["actualYieldKg"],
        "waterRequirement": cfg["water_requirement"],
        "risk": risk,
        "finalHealth": state["cropHealth"],
        "waterUsedLitres": round(state["waterUsedLitres"], 1),
        "durationDays": cfg["duration_days"],
    }

