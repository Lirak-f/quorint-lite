"""Loads the correct sector YAML config based on HS code chapter prefix."""

import os
from pathlib import Path
from typing import Any

import yaml

_CONFIGS_DIR = Path(__file__).parent / "configs"

HS_CHAPTER_TO_SECTOR: dict[str, str] = {
    "44": "furniture_wood",
    "94": "furniture_wood",
    "61": "textiles_apparel",
    "62": "textiles_apparel",
    "63": "textiles_apparel",
    "07": "food_beverage",
    "08": "food_beverage",
    "09": "food_beverage",
    "15": "food_beverage",
    "16": "food_beverage",
    "17": "food_beverage",
    "18": "food_beverage",
    "19": "food_beverage",
    "20": "food_beverage",
    "21": "food_beverage",
    "22": "food_beverage",
    "72": "metals_steel",
    "73": "metals_steel",
    "84": "machinery",
    "85": "machinery",
    "87": "auto_parts",
}

_cache: dict[str, dict[str, Any]] = {}


def load_sector_config(hs_code: str) -> dict[str, Any]:
    """Return the sector YAML config for the given HS code (4 or 6 digits)."""
    chapter = hs_code[:2].zfill(2)
    sector = HS_CHAPTER_TO_SECTOR.get(chapter)
    if not sector:
        raise ValueError(f"No sector config for HS chapter {chapter} (hs_code={hs_code})")

    if sector not in _cache:
        config_path = _CONFIGS_DIR / f"{sector}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Sector config not found: {config_path}")
        with config_path.open() as f:
            _cache[sector] = yaml.safe_load(f)

    return _cache[sector]
