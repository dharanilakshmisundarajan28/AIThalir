"""
Scenario ("What-If") engine for the Digital Twin dashboard.

WHY THIS FILE EXISTS
---------------------------------------------------------------------------
`simulation_engine.py` already contains the real agronomic model (growth
stages, weather, pests/disease, nutrient decay, harvest timing) and
`explainability.py` already contains the XAI layer. This module does NOT
re-implement any of that physics. It only:

  1. Turns a farmer-facing "scenario" (Rainfall Decrease -20%, More
     Fertilizer, Drip Irrigation, Heat Increase, Pest Pressure Increase, ...)
     into the numeric farm_data overrides `simulation_engine.new_state()`
     already understands.
  2. Runs a full season through the existing engine functions
     (`new_state`, `advance_day`, `perform_action`, `harvest`) with a
     lightweight autopilot identical in spirit to
     `simulation_engine.run_headless_simulation`, but exposes initial
     pest/disease seeding, which the packaged helper does not.
  3. Converts the resulting state into the yield / profit / risk / impact
     summary shown on the "Simulation Result" and "Field Dashboard" cards,
     and produces plain-language explanations for the farmer.

Nothing here should be treated as calibrated agronomic truth — the price
table and the market-demand tiers are explicitly-labelled placeholders so a
real pricing/market feed (e.g. the existing mandi_prices module) can be
swapped in later without touching the rest of the dashboard.
"""

from app.digital_twin.crop_catalog import get_crop_catalog, normalise_crop
from app.digital_twin import simulation_engine as engine
import re


# ---------------------------------------------------------------------------
# 1. Scenario presets
# ---------------------------------------------------------------------------
# Every scenario is expressed as *relative* adjustments applied on top of the
# crop's own ideal baseline (see `_baseline_farm_data`). Percentages are
# farmer-editable in the UI (the "-20%" dropdown in the mock-up); `default`
# is what is used if the farmer does not change the dropdown.

SCENARIOS = {
    "baseline": {
        "label": "Normal Conditions (Baseline)",
        "description": "Ideal conditions for this crop, used as the comparison point.",
        "adjustable": False,
    },
    "rainfall_decrease": {
        "label": "Rainfall Decrease",
        "description": "Less rain than ideal during the growing season.",
        "adjustable": True,
        "options": [-10, -20, -30, -40],
        "default": -20,
        "apply": lambda pct, fd: fd.update(
            rainfall=fd["rainfall"] * (1 + pct / 100.0),
            soilMoisture=max(10.0, fd["soilMoisture"] * (1 + (pct / 100.0) * 1.5)),
        ),
    },
    "more_fertilizer": {
        "label": "More Fertilizer",
        "description": "Nitrogen, phosphorus and potassium applied above the ideal level.",
        "adjustable": True,
        "options": [15, 25, 40],
        "default": 25,
        "cost_multiplier": lambda pct: 1 + (pct / 100.0) * 0.6,
        "apply": lambda pct, fd: fd.update(
            nitrogen=fd["nitrogen"] * (1 + pct / 100.0),
            phosphorus=fd["phosphorus"] * (1 + pct / 100.0),
            potassium=fd["potassium"] * (1 + pct / 100.0),
        ),
    },
    "less_fertilizer": {
        "label": "Less Fertilizer",
        "description": "Nitrogen, phosphorus and potassium applied below the ideal level.",
        "adjustable": True,
        "options": [-15, -25, -40],
        "default": -25,
        "cost_multiplier": lambda pct: 1 + (pct / 100.0) * 0.6,
        "apply": lambda pct, fd: fd.update(
            nitrogen=max(5.0, fd["nitrogen"] * (1 + pct / 100.0)),
            phosphorus=max(5.0, fd["phosphorus"] * (1 + pct / 100.0)),
            potassium=max(5.0, fd["potassium"] * (1 + pct / 100.0)),
        ),
    },
    "drip_irrigation": {
        "label": "Drip Irrigation",
        "description": "Consistent, efficient watering that keeps soil moisture close to ideal.",
        "adjustable": False,
        "cost_multiplier": lambda pct=None: 1.12,
        "apply": lambda pct, fd: fd.update(
            soilMoisture=(fd["ideal_moisture_mid"]),
            irrigation=40.0,
        ),
    },
    "heat_increase": {
        "label": "Heat Increase",
        "description": "Higher-than-ideal temperature through the season (heat wave risk).",
        "adjustable": True,
        "options": [3, 5, 8],
        "default": 5,
        "apply": lambda pct, fd: fd.update(temperature=fd["temperature"] + pct),
    },
    "pest_pressure_increase": {
        "label": "Pest Pressure Increase",
        "description": "Higher starting pest activity than usual for this crop/season.",
        "adjustable": True,
        "options": [20, 35, 50],
        "default": 35,
        "apply": lambda pct, fd: fd.update(initial_pest_level=pct),
    },
}

# Full parameter catalogue for the "Advanced Parameters" panel. Only the
# first group is actually consumed by simulation_engine today; the second
# group ("proxy" params) are applied as small, clearly-flagged modifiers so
# the UI can honour the full requested parameter list without pretending
# they are physically modelled to the same fidelity.
CORE_PARAMETERS = [
    {"key": "temperature", "label": "Temperature", "unit": "\u00b0C", "min": 8, "max": 45,
     "tooltip": "Average air temperature during the season. Most crops prefer a specific range; too far outside it slows growth or burns leaves."},
    {"key": "rainfall", "label": "Rainfall", "unit": "mm", "min": 0, "max": 400,
     "tooltip": "Total rainfall through the season. Drives soil moisture; too little causes drought stress, too much causes waterlogging."},
    {"key": "humidity", "label": "Humidity", "unit": "%", "min": 10, "max": 100,
     "tooltip": "Air moisture level. Very high humidity increases disease risk; very low humidity increases water loss from leaves."},
    {"key": "nitrogen", "label": "Nitrogen (N)", "unit": "kg/acre", "min": 0, "max": 160,
     "tooltip": "Drives leaf growth and green colour. Too little causes yellowing; too much can delay flowering."},
    {"key": "phosphorus", "label": "Phosphorus (P)", "unit": "kg/acre", "min": 0, "max": 100,
     "tooltip": "Supports root development and earlier flowering."},
    {"key": "potassium", "label": "Potassium (K)", "unit": "kg/acre", "min": 0, "max": 100,
     "tooltip": "Strengthens stems and improves resistance to disease and lodging."},
    {"key": "ph", "label": "Soil pH", "unit": "", "min": 4.0, "max": 9.0,
     "tooltip": "Soil acidity/alkalinity. Outside 6.0-7.5 most crops struggle to absorb nutrients even if they are present in the soil."},
    {"key": "soilMoisture", "label": "Soil Moisture", "unit": "%", "min": 5, "max": 100,
     "tooltip": "Water currently held in the soil. Each crop has an ideal band; outside it the crop is either drought-stressed or waterlogged."},
]
PROXY_PARAMETERS = [
    {"key": "organic_carbon", "label": "Organic Carbon", "unit": "%", "min": 0.2, "max": 2.0, "default": 0.8,
     "tooltip": "Soil organic matter. Higher values slightly improve nutrient retention and drought resilience (applied as a small health bonus)."},
    {"key": "sunlight", "label": "Sunlight", "unit": "hrs/day", "min": 3, "max": 12, "default": 8,
     "tooltip": "Daily sunlight hours. Low sunlight slightly slows growth (applied as a small health penalty below 6 hrs)."},
    {"key": "wind_speed", "label": "Wind Speed", "unit": "km/h", "min": 0, "max": 60, "default": 10,
     "tooltip": "Sustained wind speed. High wind increases water loss and lodging risk for tall crops (small penalty above 30 km/h)."},
    {"key": "co2", "label": "CO\u2082 Level", "unit": "ppm", "min": 350, "max": 550, "default": 415,
     "tooltip": "Ambient CO\u2082. Slightly boosts photosynthesis at higher levels (small bonus above 450 ppm)."},
    {"key": "disease_risk", "label": "Disease Risk", "unit": "%", "min": 0, "max": 100, "default": 0,
     "tooltip": "Starting disease pressure for the season, e.g. from a nearby outbreak or humid microclimate."},
]

# Placeholder economics table (kept intentionally small/simple and clearly
# separate from real market data). Replace with a live feed from the mandi
# price module for production use.
_DEFAULT_ECON = {"price_per_kg": 25, "cost_per_acre": 15000}
CROP_ECONOMICS = {
    "rice": {"price_per_kg": 20, "cost_per_acre": 15000},
    "maize": {"price_per_kg": 18, "cost_per_acre": 10000},
    "cotton": {"price_per_kg": 60, "cost_per_acre": 20000},
    "sugarcane": {"price_per_kg": 3, "cost_per_acre": 30000},
    "banana": {"price_per_kg": 10, "cost_per_acre": 25000},
    "coconut": {"price_per_kg": 35, "cost_per_acre": 30000},
    "mango": {"price_per_kg": 40, "cost_per_acre": 25000},
    "turmeric": {"price_per_kg": 70, "cost_per_acre": 20000},
    "grapes": {"price_per_kg": 50, "cost_per_acre": 30000},
    "coffee": {"price_per_kg": 150, "cost_per_acre": 30000},
}

# Very rough demand tiers so the "Market Demand" card in the mock-up has
# something meaningful to show. Marked clearly as a heuristic.
_HIGH_DEMAND_CROPS = {"rice", "maize", "cotton", "banana", "turmeric", "coconut", "mango"}


def _economics_for(crop_key):
    return CROP_ECONOMICS.get(crop_key, _DEFAULT_ECON)


def _baseline_farm_data(crop_key, acreage=1.0):
    cfg = get_crop_catalog(crop_key)
    lo, hi = cfg["ideal_moisture"]
    t_lo, t_hi = cfg["temp_ideal_range"]
    band = hi - lo
    t_band = t_hi - t_lo
    return {
        "nitrogen": cfg["ideal_npk"]["n"],
        "phosphorus": cfg["ideal_npk"]["p"],
        "potassium": cfg["ideal_npk"]["k"],
        # Slightly warm/dry-of-centre, not the mathematical midpoint - a real
        # field is rarely sitting exactly in the middle of the ideal band,
        # and this lets scenario deltas below actually cross the threshold
        # instead of staying invisibly inside a wide "still fine" zone.
        "temperature": t_lo + t_band * 0.75,
        "humidity": 65.0,
        "rainfall": 120.0,
        "ph": 6.5,
        "soilMoisture": lo + band * 0.25,
        "ideal_moisture_mid": (lo + hi) / 2.0,  # helper only, stripped before use
        "irrigation": 0.0,
        "acreage": acreage,
        "initial_pest_level": 0.0,
    }


def _run_season(crop_key, farm_data, rng_seed=42):
    """Evaluate a scenario as a steady-state condition held through the
    season, rather than a noisy day-by-day playthrough.

    Why: `simulation_engine`'s day-by-day autopilot (used by the continuous
    Digital Twin session at /digital-twin/simulator/<id>) auto-corrects
    irrigation and fertilizer every day. That is exactly right for a farmer
    actively managing a live twin, but wrong for this dashboard: it silently
    erases the very differences ("More Fertilizer" vs "Less Fertilizer",
    "Rainfall Decrease") the farmer is trying to compare, because both
    converge back to the same auto-corrected level within a few days.

    Instead we build one state from the scenario's parameters and score it
    with the engine's own health formula (`_weighted_health`) held
    constant for the season - matching how the reference dashboard presents
    a single before/after result per scenario, not a growth animation. The
    continuous, day-by-day playthrough with weather events and farmer
    actions is untouched and still lives at /digital-twin/simulator/<id>.
    """
    cfg = get_crop_catalog(crop_key)
    clean_farm_data = {k: v for k, v in farm_data.items()
                        if k not in ("ideal_moisture_mid", "initial_pest_level")}
    state = engine.new_state(crop_key, clean_farm_data)

    initial_pest = float(farm_data.get("initial_pest_level", 0) or 0)
    if initial_pest:
        state["pestLevel"] = min(100.0, initial_pest)

    # simulationDay is set to mid-season so growth-stage/maturity readouts
    # are meaningful even though this is a steady-state evaluation.
    state["simulationDay"] = cfg["duration_days"] // 2
    state["durationDays"] = cfg["duration_days"]
    state["cropHealth"] = engine._weighted_health(state, cfg)

    health_factor = state["cropHealth"] / 100.0
    base_total = cfg["base_yield_per_acre_kg"] * state["acreage"]
    state["expectedYieldKg"] = round(base_total * (0.4 + 0.6 * health_factor), 1)
    state["actualYieldKg"] = state["expectedYieldKg"]
    state["waterUsedLitres"] = round(state.get("irrigation", 0) * state["acreage"] * cfg["duration_days"] / 30.0, 1)
    state["availableActions"] = ["irrigate"] if state["soilMoisture"] < cfg["ideal_moisture"][0] else []
    state["status"] = "harvested" if state["cropHealth"] > 15 else "failed"
    return state


def _apply_proxy_modifiers(state, proxies):
    """Small, clearly-flagged adjustments for parameters the core engine
    does not model (organic carbon, sunlight, wind, CO2). Applied once to
    the final health score, never to core physics."""
    bonus = 0.0
    organic_carbon = proxies.get("organic_carbon", 0.8)
    sunlight = proxies.get("sunlight", 8)
    wind_speed = proxies.get("wind_speed", 10)
    co2 = proxies.get("co2", 415)

    bonus += (organic_carbon - 0.8) * 6         # richer soil -> small resilience bonus
    bonus += -3 if sunlight < 6 else (2 if sunlight > 9 else 0)
    bonus += -3 if wind_speed > 30 else 0
    bonus += 2 if co2 > 450 else 0

    state["cropHealth"] = max(0.0, min(100.0, state["cropHealth"] + bonus))
    return state


def _risk_label(health, disease_level, pest_level):
    score = (100 - health) * 0.5 + disease_level * 0.3 + pest_level * 0.2
    if score < 20:
        return "Low"
    if score < 45:
        return "Medium"
    return "High"


def _category(value, low_bad, high_good):
    if value >= high_good:
        return "Low"
    if value >= low_bad:
        return "Moderate"
    return "High"


def compute_scenario(crop, scenario_key="baseline", pct=None, overrides=None, acreage=1.0):
    """Run one scenario end-to-end and return everything the 3 dashboard
    views (parameters -> impact -> field) need.
    """
    crop_key = normalise_crop(crop)
    cfg = get_crop_catalog(crop_key)
    overrides = overrides or {}
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["baseline"])

    farm_data = _baseline_farm_data(crop_key, acreage)
    core_keys = {p["key"] for p in CORE_PARAMETERS}
    proxies = {p["key"]: p.get("default") for p in PROXY_PARAMETERS}

    # Manual per-parameter overrides (from the Advanced Parameters sliders)
    for key, value in overrides.items():
        if value in (None, ""):
            continue
        if key in core_keys:
            farm_data[key] = float(value)
        elif key == "disease_risk":
            farm_data["initial_pest_level"] = farm_data.get("initial_pest_level", 0)
        elif key in proxies:
            proxies[key] = float(value)

    initial_disease = float(overrides.get("disease_risk", 0) or 0)

    # Named scenario preset (applied after manual overrides so a scenario can
    # still be explored together with fine-tuned sliders)
    pct_used = None
    cost_multiplier = 1.0
    if scenario_key != "baseline":
        pct_used = pct if pct is not None else scenario.get("default")
        scenario["apply"](pct_used, farm_data)
        if "cost_multiplier" in scenario:
            cost_multiplier = scenario["cost_multiplier"](pct_used)

    state = _run_season(crop_key, farm_data, rng_seed=42)
    if initial_disease:
        state["diseaseLevel"] = min(100.0, max(state["diseaseLevel"], initial_disease))
    state = _apply_proxy_modifiers(state, proxies)

    econ = _economics_for(crop_key)
    yield_kg = state["actualYieldKg"] or state["expectedYieldKg"]
    yield_per_acre = yield_kg / acreage if acreage else yield_kg
    revenue = yield_kg * econ["price_per_kg"]
    cost = econ["cost_per_acre"] * acreage * cost_multiplier
    profit = revenue - cost
    risk = _risk_label(state["cropHealth"], state["diseaseLevel"], state["pestLevel"])
    success_rate = round(max(5.0, min(97.0, state["cropHealth"] - (state["diseaseLevel"] * 0.2))), 1)

    lo, hi = cfg["ideal_moisture"]
    water_stress = _category(state["soilMoisture"], lo * 0.6, lo)
    crop_health_cat = "Good" if state["cropHealth"] >= 70 else ("Moderate" if state["cropHealth"] >= 45 else "Stressed")
    disease_cat = _category(100 - state["diseaseLevel"], 65, 85)
    market_demand = "High" if crop_key in _HIGH_DEMAND_CROPS else "Moderate"

    result = {
        "crop": cfg["display_name"],
        "scenario_key": scenario_key,
        "scenario_label": scenario["label"],
        "scenario_pct": pct_used,
        "expected_yield_per_acre": round(yield_per_acre / 1000.0, 2),  # tons/acre
        "expected_profit": round(profit, 0),
        "expected_revenue": round(revenue, 0),
        "expected_cost": round(cost, 0),
        "risk_level": risk,
        "success_rate": success_rate,
        "crop_health_percent": round(state["cropHealth"], 1),
        "crop_health_category": crop_health_cat,
        "water_stress": water_stress,
        "disease_risk_category": disease_cat,
        "market_demand": market_demand,
        "water_used_litres": round(state["waterUsedLitres"], 1),
        "duration_days": state["durationDays"],
        "simulation_day": state["simulationDay"],
        "good_area_percent": round(state["cropHealth"]),
        "stressed_area_percent": round(100 - state["cropHealth"]),
        "next_irrigation_days": 0 if "irrigate" in state.get("availableActions", []) else 2,
        "farm_data": farm_data,
        "final_state_summary": {
            "soilMoisture": round(state["soilMoisture"], 1),
            "temperature": round(state["temperature"], 1),
            "nitrogen": round(state["nitrogen"], 1),
            "phosphorus": round(state["phosphorus"], 1),
            "potassium": round(state["potassium"], 1),
            "pestLevel": round(state["pestLevel"], 1),
            "diseaseLevel": round(state["diseaseLevel"], 1),
        },
    }
    return result


def compare_to_baseline(crop, scenario_key, pct=None, overrides=None, acreage=1.0):
    """Runs both the baseline and the requested scenario, returning the
    scenario result plus % deltas vs baseline (used for the impact card)."""
    baseline = compute_scenario(crop, "baseline", acreage=acreage)
    scenario = compute_scenario(crop, scenario_key, pct=pct, overrides=overrides, acreage=acreage)

    def pct_delta(new, old):
        if not old:
            return 0.0
        return round((new - old) / abs(old) * 100.0, 1)

    scenario["deltas"] = {
        "yield_pct": pct_delta(scenario["expected_yield_per_acre"], baseline["expected_yield_per_acre"]),
        "profit_pct": pct_delta(scenario["expected_profit"], baseline["expected_profit"]),
        "success_rate_pct": pct_delta(scenario["success_rate"], baseline["success_rate"]),
    }
    scenario["baseline"] = baseline
    scenario["explanation"] = _build_explanation(crop, scenario, baseline)
    scenario["ai_suggestion"] = _build_suggestion(crop, scenario, acreage)
    return scenario


def simulate_farmer_question(crop, question, baseline):
    """Turn a farmer's plain-language what-if question into one deterministic
    dashboard scenario.  The original recommendation economics remain the
    baseline; impacts are composed so combined conditions stay repeatable.
    """
    text = (question or "").lower()
    crop_cfg = get_crop_catalog(normalise_crop(crop))

    def percent(default):
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        return float(match.group(1)) if match else float(default)

    def percent_for(words, default):
        for word in words:
            after = re.search(word + r"[^.]{0,36}?(\d+(?:\.\d+)?)\s*%", text)
            before = re.search(r"(\d+(?:\.\d+)?)\s*%[^.]{0,36}?" + word, text)
            match = after or before
            if match:
                return float(match.group(1))
        return percent(default)

    def number_before(word, default):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:days?|degrees?|°c)?\s*(?:of\s+)?" + word, text)
        return float(match.group(1)) if match else float(default)

    impacts, changes = [], []
    cost_factor = 1.0

    if any(term in text for term in ("fertilizer", "fertiliser", "nutrient")):
        amount = percent_for(("fertilizer", "fertiliser", "nutrient"), 20)
        if any(term in text for term in ("reduce", "reduces", "reduced", "decrease", "decreases", "less", "lower", "cut", "cannot afford")):
            impacts.append(-min(42.0, amount * 0.45))
            cost_factor *= max(0.45, 1 - amount / 100.0)
            changes.append(f"fertilizer reduced by {amount:g}%")
        elif any(term in text for term in ("increase", "increases", "increased", "more", "add")):
            impacts.append(min(12.0, amount * 0.20))
            cost_factor *= 1 + amount / 100.0
            changes.append(f"fertilizer increased by {amount:g}%")

    if any(term in text for term in ("water", "irrigation")):
        amount = percent_for(("water", "irrigation"), 20)
        if any(term in text for term in ("reduce", "reduces", "reduced", "decrease", "decreases", "less", "low", "shortage", "insufficient")):
            impacts.append(-min(48.0, amount * 0.55))
            changes.append(f"water reduced by {amount:g}%")
        elif any(term in text for term in ("increase", "more", "improve")):
            impacts.append(min(10.0, amount * 0.15))
            changes.append(f"water increased by {amount:g}%")

    if "no rain" in text or "without rain" in text:
        days = number_before("days", 10)
        impacts.append(-min(50.0, days * 2.0))
        changes.append(f"no rain for {days:g} days")
    elif any(term in text for term in ("rainfall", "rain")):
        amount = percent_for(("rainfall", "rain"), 20)
        if any(term in text for term in ("reduce", "reduces", "reduced", "decrease", "decreases", "less", "low")):
            impacts.append(-min(42.0, amount * 0.38))
            changes.append(f"rainfall reduced by {amount:g}%")
        elif any(term in text for term in ("heavy", "excess", "flood", "increase", "more")):
            impacts.append(-min(35.0, max(12.0, amount * 0.25)))
            changes.append("excess rainfall")

    if any(term in text for term in ("temperature", "heat", "hotter", "warmer", "cold", "cooler")):
        degrees = number_before("degrees", 3)
        direction = -1 if any(term in text for term in ("decrease", "lower", "cooler", "cold")) else 1
        lo, hi = crop_cfg["temp_ideal_range"]
        sensitivity = 2.4 if direction > 0 else 2.0
        impacts.append(-min(30.0, abs(degrees) * sensitivity))
        changes.append(f"temperature {'increased' if direction > 0 else 'decreased'} by {degrees:g}°C")

    if any(term in text for term in ("delay planting", "planting delay", "delay sowing", "late planting")):
        days = number_before("days", 15)
        impacts.append(-min(35.0, days * 0.65))
        changes.append(f"planting delayed by {days:g} days")

    if any(term in text for term in ("pest", "disease", "insect")):
        amount = percent_for(("pest", "disease", "insect"), 30)
        impacts.append(-min(45.0, amount * 0.42))
        changes.append(f"pest or disease pressure increased by {amount:g}%")

    if not impacts:
        changes.append("no measurable farm condition was found")

    impact = max(-75.0, min(15.0, sum(impacts)))
    growth = round(max(5.0, min(100.0, 100.0 + impact)), 1)
    yield_factor = growth / 100.0
    base_yield = baseline.get("expected_yield_tons")
    base_income = baseline.get("expected_income")
    base_cost = baseline.get("expected_cost")
    base_profit = baseline.get("expected_profit")
    expected_yield = round(float(base_yield) * yield_factor, 2) if base_yield is not None else None
    if base_income is not None and base_cost is not None:
        expected_profit = round(float(base_income) * yield_factor - float(base_cost) * cost_factor, 0)
    else:
        expected_profit = round(float(base_profit) * yield_factor, 0) if base_profit is not None else None

    return {
        "recognized": bool(impacts),
        "changes": changes,
        "growth": growth,
        "impact_pct": round(impact, 1),
        "expected_yield_tons": expected_yield,
        "expected_profit": expected_profit,
        "yield_change": round(expected_yield - float(base_yield), 2) if expected_yield is not None and base_yield is not None else None,
        "profit_change": round(expected_profit - float(base_profit), 0) if expected_profit is not None and base_profit is not None else None,
        "visual_health": growth,
        "message": _farmer_message(changes, impact),
        "tip": _farmer_tip(changes, impact),
    }


def _farmer_message(changes, impact):
    if not impact:
        return "I could not find a measurable condition to simulate. Try mentioning water, fertilizer, rain, temperature, planting delay, or pests."
    direction = "improve" if impact > 0 else "reduce"
    return f"With {', '.join(changes)}, crop growth may {direction}. The expected yield and profit are updated below for this scenario."


def _farmer_tip(changes, impact):
    if impact < -20:
        return "This condition could put the crop under stress. If possible, correct the biggest water, nutrient, or pest issue early."
    if impact < 0:
        return "Watch the crop closely and keep water and nutrients balanced to protect yield."
    if impact > 0:
        return "This change may help, but avoid excess inputs so the crop stays balanced."
    return "Current conditions are the reference plan for this crop."


# ---------------------------------------------------------------------------
# Plain-language explanation (farmer-facing, not technical SHAP language)
# ---------------------------------------------------------------------------

def _build_explanation(crop, scenario, baseline):
    reasons = []
    fs = scenario["final_state_summary"]
    cfg = get_crop_catalog(normalise_crop(crop))

    if scenario["scenario_pct"] is not None and scenario["scenario_key"] != "baseline":
        sign = "increased" if scenario["scenario_pct"] > 0 else "decreased"
        reasons.append(f"{scenario['scenario_label']} — value {sign} by {abs(scenario['scenario_pct'])}% versus normal conditions.")

    ideal = cfg["ideal_npk"]
    if fs["nitrogen"] < ideal["n"] * 0.7:
        reasons.append("Nitrogen is below the ideal level, which limits leaf growth and lowers yield.")
    elif fs["nitrogen"] <= ideal["n"] * 1.3:
        reasons.append("Nitrogen is within the optimum range for this crop.")
    else:
        reasons.append("Nitrogen is higher than needed, which can delay flowering.")

    if fs["phosphorus"] >= ideal["p"]:
        reasons.append("Root growth improved because phosphorus is at or above the ideal level.")

    t_lo, t_hi = cfg["temp_ideal_range"]
    if fs["temperature"] > t_hi:
        reasons.append("High temperature reduced flowering and increased water loss from the crop.")
    elif fs["temperature"] < t_lo:
        reasons.append("Lower-than-ideal temperature is slowing down growth.")

    lo, hi = cfg["ideal_moisture"]
    if fs["soilMoisture"] < lo:
        reasons.append("Soil moisture is below the ideal band, causing drought stress.")
    elif fs["soilMoisture"] > cfg["waterlogging_risk_above"]:
        reasons.append("Waterlogging reduced oxygen availability to the roots.")

    if fs["diseaseLevel"] > 30:
        reasons.append(f"Disease risk is elevated ({', '.join(cfg['diseases'])}), which can reduce final yield.")
    if fs["pestLevel"] > 30:
        reasons.append(f"Pest pressure is elevated ({', '.join(cfg['pests'])}); monitoring and treatment are recommended.")

    if not reasons:
        reasons.append("Conditions are close to ideal for this crop, so results are close to the baseline.")

    return reasons[:6]


def _build_suggestion(crop, scenario, acreage):
    """If the scenario shows meaningful water stress, quantify how much
    switching to drip irrigation would help — reusing the engine itself
    rather than guessing a number."""
    if scenario["water_stress"] != "High":
        return None
    irrigated = compute_scenario(crop, "drip_irrigation", acreage=acreage)
    improvement = 0.0
    if scenario["expected_profit"]:
        improvement = round(
            (irrigated["expected_profit"] - scenario["expected_profit"]) / abs(scenario["expected_profit"]) * 100.0, 1
        )
    return {
        "text": "Install drip irrigation to reduce water stress.",
        "expected_profit_improvement_pct": improvement,
    }
