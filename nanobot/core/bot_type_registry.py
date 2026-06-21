"""Static bot-stat registry, loaded once from data/bot_types.json.
Mirrors src/core/bot_type_registry.gd."""

from __future__ import annotations

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "bot_types.json")

_data: dict = {}
_loaded = False


def _load() -> None:
    global _data, _loaded
    _loaded = True
    if not os.path.exists(DATA_PATH):
        print(f"BotTypeRegistry: data file not found: {DATA_PATH}")
        return
    with open(DATA_PATH, "r") as f:
        _data = json.load(f)


def get_type(type_name: str) -> dict:
    if not _loaded:
        _load()
    return _data.get(type_name, {})


def all_types() -> list[str]:
    if not _loaded:
        _load()
    return list(_data.keys())


def is_valid_type(type_name: str) -> bool:
    if not _loaded:
        _load()
    return type_name in _data
