"""Prediction and SHAP explanation helpers for the digital twin.

The trained recommendation artefacts are loaded through ``app.ml`` once per
process.  SHAP is used when available; a transparent agronomic fallback keeps
the simulator usable if an explanation cannot be calculated for an artefact.
"""
import numpy as np

from app.digital_twin.crop_catalog import get_crop_catalog, normalise_crop
from app.ml import load_model

FEATURES = ("nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall")
_EXPLAINER = None


def _get_explainer(model):
    """Create the TreeExplainer once; model training is never part of a request."""
    global _EXPLAINER
    if _EXPLAINER is None:
        import shap
        _EXPLAINER = shap.TreeExplainer(model)
    return _EXPLAINER


def _fallback_contributions(crop, inputs):
    cfg = get_crop_catalog(crop)
    ideal = cfg["ideal_npk"]
    ranges = {
        "nitrogen": (ideal["n"], 75), "phosphorus": (ideal["p"], 60), "potassium": (ideal["k"], 70),
        "temperature": (sum(cfg["temp_ideal_range"]) / 2, 12), "humidity": (65, 35),
        "ph": (6.5, 2), "rainfall": (120, 180),
    }
    values = []
    for name in FEATURES:
        target, span = ranges[name]
        score = max(-1.0, 1 - abs(float(inputs.get(name, target)) - target) / span)
        values.append({"feature": name, "value": round(score, 3)})
    return values


def analyse_crop(crop, inputs):
    """Return model probability plus per-feature SHAP contributions as JSON."""
    crop_key = normalise_crop(crop)
    inputs = {name: float(inputs.get(name, 0)) for name in FEATURES}
    contributions = None
    probability = None
    try:
        model, scaler, _ = load_model()
        row = np.array([[inputs[name] for name in FEATURES]])
        transformed = scaler.transform(row)
        probabilities = model.predict_proba(transformed)[0]
        class_index = list(model.classes_).index(crop_key) if crop_key in model.classes_ else int(np.argmax(probabilities))
        probability = round(float(probabilities[class_index]) * 100, 2)
        try:
            shap_values = _get_explainer(model).shap_values(transformed)
            values = np.asarray(shap_values)
            # SHAP versions expose either [class][sample][feature] or
            # [sample][feature][class] for sklearn classifiers.
            if values.ndim == 3 and values.shape[0] == 1:
                vector = values[0, :, class_index]
            elif values.ndim == 3:
                vector = values[class_index, 0, :]
            else:
                vector = values[0]
            contributions = [{"feature": name, "value": round(float(vector[index]), 4)} for index, name in enumerate(FEATURES)]
        except Exception:
            contributions = _fallback_contributions(crop_key, inputs)
    except Exception:
        contributions = _fallback_contributions(crop_key, inputs)

    contributions.sort(key=lambda item: abs(item["value"]), reverse=True)
    positives = [item["feature"] for item in contributions if item["value"] > 0][:3]
    negatives = [item["feature"] for item in contributions if item["value"] < 0][:3]
    nitrogen = inputs["nitrogen"]
    leaf_reason = "Low nitrogen can cause chlorosis." if nitrogen < get_crop_catalog(crop_key)["ideal_npk"]["n"] * .6 else "Nitrogen is supporting healthy green foliage."
    fruit_reason = "High temperature can reduce pollination and fruit set." if inputs["temperature"] > get_crop_catalog(crop_key)["temp_ideal_range"][1] else "Current temperature supports pollination and fruit formation."
    return {
        "probability": probability,
        "contributions": contributions,
        "positive": positives,
        "negative": negatives,
        "explanations": {
            "plantHeight": "Nutrients and water are the strongest growth contributors for this crop.",
            "leafColour": leaf_reason,
            "fruitCount": fruit_reason,
            "yield": "Balanced nutrient, moisture, and temperature conditions improve projected yield.",
        },
    }
