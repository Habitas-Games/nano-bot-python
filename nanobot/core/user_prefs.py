"""Tiny persistent user preferences (JSON in the project root).

Remembers what the UI shouldn't ask for twice across app restarts:
the last folder browsed for maps and for strategies (two separate
defaults), and the last map/strategy selections used for a match.
Everything is failure-tolerant — a missing, corrupt, or unwritable
prefs file degrades to defaults, never to a crash: preferences are a
convenience, not data."""

from __future__ import annotations

import json
import os

PREFS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".nanobot_prefs.json"))

KNOWN_KEYS = ("last_map_dir", "last_strategy_dir", "last_map", "last_strategies")


def load() -> dict:
    try:
        with open(PREFS_PATH, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get(key: str, default=None):
    return load().get(key, default)


def update(**kwargs) -> None:
    """Merge the given keys into the prefs file (read-modify-write —
    other keys survive)."""
    data = load()
    data.update(kwargs)
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(data, f, indent="\t")
    except OSError as e:
        print(f"user_prefs: could not save {PREFS_PATH}: {e}")


def existing_file(key: str) -> str | None:
    """A stored path, but only if it still exists on disk."""
    path = get(key)
    return path if isinstance(path, str) and os.path.isfile(path) else None


def existing_files(key: str) -> list[str]:
    """A stored path list, filtered to those that still exist."""
    paths = get(key)
    if not isinstance(paths, list):
        return []
    return [p for p in paths if isinstance(p, str) and os.path.isfile(p)]


def existing_dir(key: str, fallback: str) -> str:
    """A stored directory if it still exists, else the fallback."""
    path = get(key)
    if isinstance(path, str) and os.path.isdir(path):
        return path
    return fallback
