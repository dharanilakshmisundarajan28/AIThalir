"""Configuration catalogue shared by the crop digital twin and its renderer.

The catalogue deliberately describes crops as data.  New crops can be added
without adding another simulation code path.
"""

from copy import deepcopy


_BASE = {
    "duration_days": 120,
    "ideal_moisture": (45, 70),
    "water_requirement": "Medium",
    "drought_sensitivity": "Medium",
    "heavy_rain_sensitivity": "Medium",
    "waterlogging_risk_above": 82,
    "ideal_npk": {"n": 65, "p": 45, "k": 55},
    "npk_decay_per_day": {"n": 0.8, "p": 0.5, "k": 0.6},
    "temp_ideal_range": (20, 32),
    "pests": ["Aphids", "Leaf borer"],
    "diseases": ["Leaf spot", "Root rot"],
    "pest_base_risk": 0.05,
    "disease_base_risk": 0.04,
    "base_yield_per_acre_kg": 1000,
    "maturity_harvest_window": (95, 100),
}


# key, display name, visual form, height, spacing, duration, yield, ideal NPK,
# temperature range, fruit/flower treatment.  These values drive both the
# procedural scene and the agronomic response model.
_CROPS = [
    ("rice", "Rice", "paddy", 1.1, 0.24, 120, 1800, (70, 55, 60), (22, 32), "grain"),
    ("maize", "Maize", "stalk", 2.7, 0.72, 100, 1400, (75, 50, 55), (18, 30), "cob"),
    ("sugarcane", "Sugarcane", "palm", 8.5, 5.5, 365, 5000, (80, 30, 80), (24, 34), "cane"),
    ("jute", "Jute", "fibre", 2.8, 0.30, 120, 950, (60, 35, 45), (24, 35), "flower"),
    ("cotton", "Cotton", "bush", 1.5, 1.15, 160, 500, (60, 45, 65), (21, 35), "boll"),
    ("coconut", "Coconut", "palm", 8.5, 5.5, 365, 5000, (80, 30, 80), (24, 34), "coconut"),
    ("banana", "Banana", "banana", 4.2, 2.5, 330, 25000, (80, 35, 100), (24, 35), "bunch"),
    ("mango", "Mango", "tree", 6.5, 5.0, 365, 8000, (70, 30, 70), (24, 35), "mango"),
    ("orange", "Orange", "tree", 4.5, 4.0, 300, 10000, (65, 35, 70), (18, 32), "orange"),
    ("papaya", "Papaya", "papaya", 3.8, 2.2, 270, 15000, (80, 40, 90), (22, 34), "papaya"),
    ("watermelon", "Watermelon", "vine", 0.35, 2.4, 100, 12000, (45, 30, 55), (24, 35), "watermelon"),
    ("muskmelon", "Muskmelon", "vine", 0.35, 2.2, 95, 9000, (45, 30, 55), (22, 34), "muskmelon"),
    ("apple", "Apple", "tree", 4.8, 4.5, 300, 6000, (60, 35, 70), (15, 28), "apple"),
    ("grapes", "Grapes", "trellis", 2.1, 2.0, 180, 7000, (65, 35, 70), (18, 32), "grape"),
    ("pomegranate", "Pomegranate", "tree", 3.6, 3.5, 240, 8000, (55, 30, 65), (20, 35), "pomegranate"),
    ("coffee", "Coffee", "shrub", 2.1, 2.1, 300, 500, (45, 35, 60), (18, 28), "cherry"),
    ("chickpea", "Chickpea", "legume", 0.55, 0.35, 110, 900, (25, 35, 45), (15, 28), "pod"),
    ("kidneybeans", "Kidney Beans", "legume", 0.65, 0.38, 110, 800, (30, 40, 45), (18, 30), "pod"),
    ("blackgram", "Black Gram", "legume", 0.50, 0.32, 90, 700, (25, 35, 40), (22, 32), "pod"),
    ("mungbean", "Mung Bean", "legume", 0.48, 0.30, 80, 650, (25, 35, 40), (22, 34), "pod"),
    ("mothbeans", "Moth Beans", "legume", 0.38, 0.30, 85, 600, (20, 30, 35), (24, 36), "pod"),
    ("pigeonpeas", "Pigeon Peas", "legume", 1.8, 0.9, 160, 900, (35, 40, 45), (20, 34), "pod"),
    ("turmeric", "Turmeric", "turmeric", 1.0, 0.7, 240, 1000, (60, 35, 70), (20, 35), "rhizome"),
]


def _stages(duration, fruit_name):
    points = [0, .06, .20, .48, .66, .86, 1]
    names = ["Seed", "Germination", "Vegetative", "Flowering", f"{fruit_name.title()} Formation", "Maturity", "Harvest"]
    starts = [round(duration * point) for point in points]
    return [(name, start, (starts[index + 1] - 1) if index < len(starts) - 1 else duration) for index, (name, start) in enumerate(zip(names, starts))]


def _build_catalog():
    catalog = {}
    for key, name, form, height, spacing, duration, yield_kg, npk, temp, fruit in _CROPS:
        entry = deepcopy(_BASE)
        entry.update({
            "display_name": name, "duration_days": duration,
            "growth_stages": _stages(duration, fruit), "base_yield_per_acre_kg": yield_kg,
            "ideal_npk": {"n": npk[0], "p": npk[1], "k": npk[2]}, "temp_ideal_range": temp,
            "visual": {"form": form, "height": height, "spacing": spacing, "fruit": fruit,
                       "model": f"models/{key}.glb"},
        })
        if form in ("paddy", "banana", "palm"):
            entry.update({"ideal_moisture": (60, 85), "water_requirement": "High", "drought_sensitivity": "High"})
        if form == "vine":
            entry.update({"ideal_moisture": (50, 75), "heavy_rain_sensitivity": "High"})
        catalog[key] = entry
    return catalog


CROP_CATALOG = _build_catalog()
ALIASES = {"kidney beans": "kidneybeans", "black gram": "blackgram", "mung bean": "mungbean", "moth beans": "mothbeans", "pigeon peas": "pigeonpeas"}


def normalise_crop(crop):
    key = (crop or "rice").strip().lower().replace("_", " ")
    return ALIASES.get(key, key.replace(" ", ""))


def get_crop_catalog(crop):
    return CROP_CATALOG.get(normalise_crop(crop), CROP_CATALOG["rice"])
