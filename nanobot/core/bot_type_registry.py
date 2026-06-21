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
    _loaded = True  # set early to prevent re-entrant calls on error
    if not os.path.exists(DATA_PATH):
        print(f"BotTypeRegistry: data file not found: {DATA_PATH}")
        return
    with open(DATA_PATH, "r") as f:
        try:
            parsed = json.load(f)
        except json.JSONDecodeError as e:
            # The Godot original checks json.parse(...) != OK here; the
            # initial Python port used json.load() directly with no
            # try/except, which let a malformed data file crash with an
            # unhandled JSONDecodeError instead of failing gracefully like
            # this same function's missing-file case already did, and
            # like the Godot version it was ported from already does.
            print(f"BotTypeRegistry: JSON parse error in {DATA_PATH}: {e}")
            return

    if not isinstance(parsed, dict):
        # Syntactically valid JSON that isn't an object (e.g. a bare
        # array) parses without error but isn't usable as a stats table —
        # get_type()'s _data.get(...) would crash with an AttributeError
        # on first call otherwise. Treat it the same as a parse failure.
        print(f"BotTypeRegistry: expected a JSON object in {DATA_PATH}, got {type(parsed).__name__}")
        return

    _data = parsed


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
