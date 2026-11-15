"""Configuration loading and saving."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_settings(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else SETTINGS_PATH
    with open(p, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def save_settings(settings: dict[str, Any], path: Path | str | None = None) -> None:
    p = Path(path) if path else SETTINGS_PATH
    with open(p, "w", encoding="utf-8") as fh:
        yaml.safe_dump(settings, fh, sort_keys=False, allow_unicode=True)


def resolve_path(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else PROJECT_ROOT / p


def label(settings: dict, field: str, code: Any) -> str:
    """Human label for a code; falls back to the code itself."""
    if code is None or (isinstance(code, float) and code != code):
        return "Unknown"
    labels = (settings.get("labels") or {}).get(field) or {}
    key = str(code)
    return str(labels.get(key, key))


def deep_copy(settings: dict) -> dict:
    return copy.deepcopy(settings)
