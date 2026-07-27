"""Compatibility façade for the data-driven crop digital-twin catalogue."""
from app.digital_twin.crop_catalog import CROP_CATALOG, get_crop_catalog, normalise_crop

CROP_CONFIG = CROP_CATALOG
DEFAULT_CROP_KEY = "rice"

def get_crop_config(crop_name):
    return get_crop_catalog(crop_name)

def get_stage_for_day(crop_name, day):
    cfg = get_crop_config(crop_name)
    for name, start, end in cfg["growth_stages"]:
        if start <= day <= end:
            return name
    return cfg["growth_stages"][-1][0]

def get_maturity_percent(crop_name, day):
    return round(min(100.0, day / get_crop_config(crop_name)["duration_days"] * 100), 1)

def list_available_crops():
    return list(CROP_CONFIG)
