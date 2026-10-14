"""Shared helpers used by every script in src/.

Nothing in here contains business rules: those live in the config/ folder.
This module only knows how to find the project folder and read the config files.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

import yaml

# The project folder is the parent of the src/ folder this file sits in.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# Excel counts days from 30 December 1899 (a quirk inherited from Lotus 1-2-3).
EXCEL_EPOCH = dt.date(1899, 12, 30)


def load_yaml(relative_path: str) -> dict:
    """Read a YAML file from the config/ folder and return it as a Python dict."""
    with open(CONFIG_DIR / relative_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=None)
def load_settings() -> dict:
    """Main settings: config/settings.yaml."""
    return load_yaml("settings.yaml")


@lru_cache(maxsize=None)
def load_admin() -> dict:
    """Rwanda provinces and districts: config/reference/rwanda_admin.yaml."""
    return load_yaml("reference/rwanda_admin.yaml")


def district_to_province() -> dict[str, str]:
    """Return {district: province} for all 30 districts."""
    return {
        district: province
        for province, districts in load_admin()["provinces"].items()
        for district in districts
    }


def resolve_path(key: str) -> Path:
    """Turn a folder name from settings.yaml 'paths' into a full path."""
    return PROJECT_ROOT / load_settings()["paths"][key]


def fiscal_year_label(date: dt.date, start_month: int | None = None) -> str:
    """Return the Rwanda fiscal-year label for a date, e.g. 2024-03-12 -> 'FY2023/24'.

    The fiscal year runs from July (start_month = 7) to June.
    """
    if start_month is None:
        start_month = load_settings()["fiscal_year"]["start_month"]
    start = date.year if date.month >= start_month else date.year - 1
    return f"FY{start}/{str(start + 1)[-2:]}"


def to_excel_serial(date: dt.date) -> int:
    """Convert a date to the whole number Excel stores internally (e.g. 2024-03-12 -> 45363)."""
    return (date - EXCEL_EPOCH).days
