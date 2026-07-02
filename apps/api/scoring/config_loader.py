"""Loads the correct sector YAML config based on HS code chapter prefix."""

from pathlib import Path
from typing import Any

import yaml

_CONFIGS_DIR = Path(__file__).parent / "configs"

# Built once on first call by scanning all YAML files.
_HS_CHAPTER_TO_SECTOR: dict[str, str] | None = None
_cache: dict[str, dict[str, Any]] = {}


def _build_chapter_index() -> dict[str, str]:
    """Scan every *.yaml in configs/, read hs_chapters, return chapter→sector map."""
    index: dict[str, str] = {}
    for path in sorted(_CONFIGS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sector_name = path.stem
        for ch in data.get("hs_chapters", []):
            ch = str(ch).zfill(2)
            if ch in index:
                raise ValueError(
                    f"HS chapter {ch} claimed by both '{index[ch]}' and '{sector_name}'"
                )
            index[ch] = sector_name
    return index


def load_sector_config(hs_code: str) -> dict[str, Any]:
    """Return the sector YAML config for the given HS code (4 or 6 digits)."""
    global _HS_CHAPTER_TO_SECTOR
    if _HS_CHAPTER_TO_SECTOR is None:
        _HS_CHAPTER_TO_SECTOR = _build_chapter_index()

    chapter = hs_code[:2].zfill(2)
    sector = _HS_CHAPTER_TO_SECTOR.get(chapter)
    if not sector:
        raise ValueError(f"No sector config for HS chapter {chapter} (hs_code={hs_code})")

    if sector not in _cache:
        config_path = _CONFIGS_DIR / f"{sector}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Sector config not found: {config_path}")
        with config_path.open(encoding="utf-8") as f:
            _cache[sector] = yaml.safe_load(f)

    return _cache[sector]
