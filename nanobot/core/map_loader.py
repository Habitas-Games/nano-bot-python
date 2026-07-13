"""JSON <-> MapData. This is the single canonical home for both directions
of the conversion — both the simulator and the pygame map editor import
load_from_file()/save_to_file() from here rather than each having their
own. The Godot version of this project (nano-bot) split loading into two
near-identical implementations (one in the simulator's map_loader.gd, one
in the map editor) that silently drifted apart and eventually collided
under the same function name, breaking the editor outright — see that
project's docs/versioning/v0.0.3/analysis.md §2. Keeping one
implementation here is a direct response to that, not a stylistic choice.

width/height are *required* fields, matching the Godot simulator's
map_loader.gd — the editor must not silently guess a size for a map
missing either (same analysis.md, §3)."""

from __future__ import annotations

import json
import os

from nanobot.core.map_data import Density, MapData, StreamDir

_DENSITY_TO_STR = {Density.LOW: "low", Density.MEDIUM: "medium", Density.HIGH: "high", Density.BONE: "bone"}
_STR_TO_DENSITY = {v: k for k, v in _DENSITY_TO_STR.items()}
_STREAM_TO_STR = {StreamDir.NORTH: "north", StreamDir.SOUTH: "south", StreamDir.EAST: "east", StreamDir.WEST: "west"}
_STR_TO_STREAM = {v: k for k, v in _STREAM_TO_STR.items()}


def density_to_string(d: Density) -> str:
    return _DENSITY_TO_STR.get(d, "low")


def string_to_density(s: str) -> Density:
    return _STR_TO_DENSITY.get(s.lower(), Density.LOW)


def stream_to_string(s: StreamDir) -> str:
    return _STREAM_TO_STR.get(s, "")


def string_to_stream(s: str) -> StreamDir:
    return _STR_TO_STREAM.get(s.lower(), StreamDir.NONE)


def load_from_file(path: str) -> MapData | None:
    try:
        with open(path, "r") as f:
            text = f.read()
    except OSError as e:
        print(f"MapLoader: could not open {path}: {e}")
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"MapLoader: JSON error in {path} — {e}")
        return None

    return _parse(data, path)


def _parse(data: dict, path: str) -> MapData | None:
    for key in ("width", "height"):
        if key not in data:
            print(f"MapLoader: missing required field '{key}' in {path}")
            return None

    try:
        width, height = int(data["width"]), int(data["height"])
    except (TypeError, ValueError) as e:
        print(f"MapLoader: width/height must be numbers in {path}: {e}")
        return None
    if width <= 0 or height <= 0:
        print(f"MapLoader: width and height must be positive in {path} (got {width}x{height})")
        return None

    try:
        return _parse_body(data, width, height)
    except (KeyError, ValueError, TypeError) as e:
        # A hand-edited or corrupted map (non-numeric coordinate, missing
        # required key in a cell/element entry, etc.) must fail cleanly
        # here rather than raising out of the loader and taking down
        # whatever called it — confirmed this was previously possible:
        # a single cell with a non-numeric "x" crashed with an unhandled
        # ValueError instead of returning None like every other malformed-
        # input case in this function already did.
        print(f"MapLoader: malformed map data in {path}: {e}")
        return None


def _parse_body(data: dict, width: int, height: int) -> MapData:
    m = MapData(width, height)
    m.map_name = data.get("name", "Unnamed")
    m.starting_azn = int(data.get("starting_azn", 150))
    m.bonus_hold_all = max(0, int(data.get("bonus_hold_all", 0)))

    default_density = string_to_density(data.get("default_density", "low"))
    for i in range(m.width * m.height):
        m._cells[i] = {"density": default_density, "stream_dir": StreamDir.NONE}

    for cell in data.get("cells", []):
        x, y = int(cell["x"]), int(cell["y"])
        if not m.is_in_bounds(x, y):
            continue
        density = string_to_density(cell.get("density", "low"))
        stream_dir = string_to_stream(cell.get("stream", ""))
        m._cells[y * m.width + x] = {"density": density, "stream_dir": stream_dir}

    for hp in data.get("habitas_points", []):
        m.habitas_points.append((int(hp["x"]), int(hp["y"])))

    for azn in data.get("azn_nodes", []):
        m.azn_nodes.append({
            "position": (int(azn["x"]), int(azn["y"])),
            "quantity": int(azn.get("quantity", 10)),
        })

    for zone in data.get("injection_zones", []):
        x1, y1 = int(zone["x1"]), int(zone["y1"])
        x2, y2 = int(zone["x2"]), int(zone["y2"])
        m.injection_zones.append({
            "player": int(zone.get("player", 0)),
            "rect": (x1, y1, x2 - x1 + 1, y2 - y1 + 1),
        })

    for hz in data.get("hazards", []):
        path = [(int(p[0]), int(p[1])) for p in hz.get("path", [])]
        if not path:
            continue
        m.hazards.append({
            "path": path,
            "hp": int(hz.get("hp", 40)),
            "damage": int(hz.get("damage", 3)),
            "range": float(hz.get("range", 1.5)),
            "move_every": max(1, int(hz.get("move_every", 3))),
        })

    return m


def create_json(m: MapData, map_name: str | None = None, starting_azn: int | None = None) -> dict:
    """MapData -> JSON dict, using sparse cell encoding (only non-default
    cells are listed) — mirrors the Godot editor's map_io.gd.

    starting_azn defaults to the MapData's own value rather than a fixed
    150 — that field used to be write-only: every saved map always wrote
    150 regardless of what (if anything) the source MapData carried,
    because MapData itself had no such attribute and nothing ever read
    the field back out of a loaded map either. A map author setting a
    custom starting budget had no way to actually do that. Fixed
    end-to-end (MapData, load, save, SimulationCore) — see
    docs/versioning/v0.0.2/changelog.md."""
    out = {
        "name": map_name if map_name is not None else (m.map_name or "Untitled Map"),
        "width": m.width,
        "height": m.height,
        "default_density": "low",
        "starting_azn": starting_azn if starting_azn is not None else m.starting_azn,
        "cells": [],
    }
    if m.bonus_hold_all > 0:
        out["bonus_hold_all"] = m.bonus_hold_all
    out.update({
        "habitas_points": [],
        "azn_nodes": [],
        "injection_zones": [],
    })

    for i, cell in enumerate(m._cells):
        if cell["density"] != Density.LOW or cell["stream_dir"] != StreamDir.NONE:
            x, y = i % m.width, i // m.width
            cell_obj = {"x": x, "y": y, "density": density_to_string(cell["density"])}
            if cell["stream_dir"] != StreamDir.NONE:
                cell_obj["stream"] = stream_to_string(cell["stream_dir"])
            out["cells"].append(cell_obj)

    for hp in m.habitas_points:
        out["habitas_points"].append({"x": hp[0], "y": hp[1]})

    for azn in m.azn_nodes:
        out["azn_nodes"].append({"x": azn["position"][0], "y": azn["position"][1], "quantity": azn["quantity"]})

    for zone in m.injection_zones:
        rx, ry, rw, rh = zone["rect"]
        out["injection_zones"].append({
            "player": zone["player"],
            "x1": rx, "y1": ry, "x2": rx + rw - 1, "y2": ry + rh - 1,
        })

    # Hazards round-trip even though the editor has no hazard tool yet —
    # otherwise opening and re-saving a hazard-bearing map in the editor
    # would silently strip them (the same partial-snapshot data-loss trap
    # documented for starting_azn in v0.0.2).
    if m.hazards:
        out["hazards"] = [
            {"path": [[p[0], p[1]] for p in hz["path"]], "hp": hz["hp"],
             "damage": hz["damage"], "range": hz["range"], "move_every": hz["move_every"]}
            for hz in m.hazards
        ]

    return out


def save_to_file(m: MapData, path: str, map_name: str | None = None, starting_azn: int | None = None) -> bool:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(create_json(m, map_name, starting_azn), f, indent="\t")
    except OSError as e:
        print(f"MapLoader: could not save to {path}: {e}")
        return False
    return True


def validate(m: MapData) -> list[str]:
    """Returns an array of error strings describing why the map isn't ready
    to save/play. Empty = valid."""
    errors = []
    if not m.habitas_points:
        errors.append("Need at least 1 Habitas Point")
    if not m.azn_nodes:
        errors.append("Need at least 1 AZN Node")
    if not m.injection_zones:
        errors.append("Need at least 1 Injection Zone")

    # Objectives buried in Bone are unreachable/unwinnable by
    # construction — catch them at save time instead of at match time.
    for hp in m.habitas_points:
        if not m.is_passable(*hp):
            errors.append(f"Habitas Point at {hp} is on impassable terrain")
    for azn in m.azn_nodes:
        if not m.is_passable(*azn["position"]):
            errors.append(f"AZN node at {azn['position']} is on impassable terrain")
    for z in m.injection_zones:
        rx, ry, rw, rh = z["rect"]
        if not any(m.is_passable(rx + dx, ry + dy) for dx in range(rw) for dy in range(rh)):
            errors.append(f"Player {z['player'] + 1} injection zone has no passable cell")
    for i, hz in enumerate(m.hazards):
        for wp in hz["path"]:
            if not m.is_passable(wp[0], wp[1]):
                errors.append(f"White cell {i + 1} waypoint {tuple(wp)} is on impassable terrain")
                break
    return errors


def derive_map_name(filename: str) -> str:
    """'bone_maze.json' -> 'Bone Maze'. The display name doubles as the
    replay->map resolution key (the viewer matches replays to map files
    by name), so every save stamps a filename-derived name instead of
    letting new maps pile up as identical 'Untitled Map's."""
    stem = os.path.basename(filename).rsplit(".", 1)[0]
    return " ".join(w.capitalize() for w in stem.replace("_", " ").replace("-", " ").split()) or "Untitled Map"
