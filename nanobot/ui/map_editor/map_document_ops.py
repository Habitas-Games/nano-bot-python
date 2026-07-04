"""Editing operations on a core.map_data.MapData instance: paint, fill,
delete, element placement/move/resize, and undo-snapshot support.

These are free functions over MapData rather than a wrapper class, so the
editor, the simulator, and any future tooling all share the exact same
data model with no duplicate "document" type to keep in sync — the
opposite of the Godot project's MapEditor, which had its own MapDocument
class duplicating MapData's shape. One data class, one loader/saver
(map_loader.py), and this module for the mutations only the editor needs."""

from __future__ import annotations

from nanobot.core.map_data import Density, MapData, StreamDir


def init_blank(width: int, height: int, default_density: Density = Density.LOW) -> MapData:
    m = MapData(width, height)
    for i in range(width * height):
        m._cells[i] = {"density": default_density, "stream_dir": StreamDir.NONE}
    return m


def paint_cell(m: MapData, x: int, y: int, density: Density) -> None:
    if not m.is_in_bounds(x, y):
        return
    m._cells[y * m.width + x]["density"] = density


def place_stream(m: MapData, x: int, y: int, direction: StreamDir) -> None:
    if not m.is_in_bounds(x, y):
        return
    m._cells[y * m.width + x]["stream_dir"] = direction


def flood_fill(m: MapData, start_x: int, start_y: int, new_density: Density) -> None:
    if not m.is_in_bounds(start_x, start_y):
        return
    target_density = m._cells[start_y * m.width + start_x]["density"]
    if target_density == new_density:
        return

    stack = [(start_x, start_y)]
    visited = set()

    while stack:
        x, y = stack.pop()
        if not m.is_in_bounds(x, y) or (x, y) in visited:
            continue
        idx = y * m.width + x
        if m._cells[idx]["density"] != target_density:
            continue
        visited.add((x, y))
        m._cells[idx]["density"] = new_density
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])


def clear_all(m: MapData) -> None:
    """Reset terrain/streams to default and remove every element ('Clear Map')."""
    for cell in m._cells:
        cell["density"] = Density.LOW
        cell["stream_dir"] = StreamDir.NONE
    m.habitas_points.clear()
    m.azn_nodes.clear()
    m.injection_zones.clear()


def delete_at_position(m: MapData, x: int, y: int) -> None:
    """Delete terrain/stream and any element at this grid position."""
    if not m.is_in_bounds(x, y):
        return
    idx = y * m.width + x
    m._cells[idx]["density"] = Density.LOW
    m._cells[idx]["stream_dir"] = StreamDir.NONE

    pos = (x, y)
    m.habitas_points[:] = [hp for hp in m.habitas_points if hp != pos]
    m.azn_nodes[:] = [azn for azn in m.azn_nodes if azn["position"] != pos]
    m.injection_zones[:] = [z for z in m.injection_zones if not _rect_has_point(z["rect"], pos)]


# --- element placement (with duplicate-position guard) ---

def place_habitas(m: MapData, x: int, y: int) -> bool:
    if not m.is_in_bounds(x, y):
        return False
    pos = (x, y)
    if pos in m.habitas_points:
        return False
    m.habitas_points.append(pos)
    return True


def place_azn(m: MapData, x: int, y: int, quantity: int = 30) -> bool:
    if not m.is_in_bounds(x, y):
        return False
    pos = (x, y)
    if any(azn["position"] == pos for azn in m.azn_nodes):
        return False
    m.azn_nodes.append({"position": pos, "quantity": quantity})
    return True


def place_zone(m: MapData, rect: tuple[int, int, int, int], player: int = 0) -> None:
    m.injection_zones.append({"player": player, "rect": rect})


# --- element lookup / editing ---

def find_element_at(m: MapData, x: int, y: int) -> dict:
    """Returns {"type": ..., "index": ...} for the topmost element here, or {"type": "none"}."""
    pos = (x, y)

    for i, hp in enumerate(m.habitas_points):
        if hp == pos:
            return {"type": "habitas", "index": i}

    for i, azn in enumerate(m.azn_nodes):
        if azn["position"] == pos:
            return {"type": "azn", "index": i}

    for i, zone in enumerate(m.injection_zones):
        if _rect_has_point(zone["rect"], pos):
            return {"type": "zone", "index": i}

    return {"type": "none"}


def move_habitas(m: MapData, index: int, new_pos: tuple[int, int]) -> bool:
    if not m.is_in_bounds(*new_pos):
        return False
    m.habitas_points[index] = new_pos
    return True


def move_azn(m: MapData, index: int, new_pos: tuple[int, int]) -> bool:
    if not m.is_in_bounds(*new_pos):
        return False
    m.azn_nodes[index]["position"] = new_pos
    return True


def set_azn_quantity(m: MapData, index: int, quantity: int) -> None:
    m.azn_nodes[index]["quantity"] = quantity


def move_zone(m: MapData, index: int, offset: tuple[int, int]) -> bool:
    rx, ry, rw, rh = m.injection_zones[index]["rect"]
    new_x, new_y = rx + offset[0], ry + offset[1]
    if new_x < 0 or new_y < 0 or new_x + rw > m.width or new_y + rh > m.height:
        return False
    m.injection_zones[index]["rect"] = (new_x, new_y, rw, rh)
    return True


def detect_zone_corner(m: MapData, grid_x: int, grid_y: int, index: int) -> str:
    """Returns 'tl'/'tr'/'bl'/'br' if (grid_x, grid_y) is near that corner, else ''."""
    rx, ry, rw, rh = m.injection_zones[index]["rect"]
    corners = {
        "tl": (rx, ry),
        "tr": (rx + rw - 1, ry),
        "bl": (rx, ry + rh - 1),
        "br": (rx + rw - 1, ry + rh - 1),
    }
    for name, (cx, cy) in corners.items():
        if ((grid_x - cx) ** 2 + (grid_y - cy) ** 2) ** 0.5 <= 1.5:
            return name
    return ""


def resize_zone(m: MapData, index: int, corner: str, new_x: int, new_y: int) -> bool:
    rx, ry, rw, rh = m.injection_zones[index]["rect"]

    if corner == "tl":
        new_w, new_h = (rx + rw) - new_x, (ry + rh) - new_y
        if new_w < 2 or new_h < 2 or new_x < 0 or new_y < 0:
            return False
        new_rect = (new_x, new_y, new_w, new_h)
    elif corner == "tr":
        new_w, new_h = new_x - rx + 1, (ry + rh) - new_y
        if new_w < 2 or new_h < 2 or new_x >= m.width or new_y < 0:
            return False
        new_rect = (rx, new_y, new_w, new_h)
    elif corner == "bl":
        new_w, new_h = (rx + rw) - new_x, new_y - ry + 1
        if new_w < 2 or new_h < 2 or new_x < 0 or new_y >= m.height:
            return False
        new_rect = (new_x, ry, new_w, new_h)
    elif corner == "br":
        new_w, new_h = new_x - rx + 1, new_y - ry + 1
        if new_w < 2 or new_h < 2 or new_x >= m.width or new_y >= m.height:
            return False
        new_rect = (rx, ry, new_w, new_h)
    else:
        return False

    m.injection_zones[index]["rect"] = new_rect
    return True


def _rect_has_point(rect: tuple[int, int, int, int], pos: tuple[int, int]) -> bool:
    rx, ry, rw, rh = rect
    return rx <= pos[0] < rx + rw and ry <= pos[1] < ry + rh


# --- snapshot / restore (used by MapHistory for undo) ---

def snapshot(m: MapData) -> dict:
    return {
        "width": m.width,
        "height": m.height,
        "starting_azn": m.starting_azn,
        "cells": [dict(c) for c in m._cells],
        "habitas_points": list(m.habitas_points),
        "azn_nodes": [dict(a) for a in m.azn_nodes],
        "injection_zones": [dict(z) for z in m.injection_zones],
        "hazards": [{**hz, "path": list(hz["path"])} for hz in m.hazards],
    }


def restore(m: MapData, snap: dict) -> None:
    m.width = snap["width"]
    m.height = snap["height"]
    m.starting_azn = snap.get("starting_azn", 150)  # .get(): tolerate pre-existing snapshots taken before this field existed
    m._cells = [dict(c) for c in snap["cells"]]
    m.habitas_points = list(snap["habitas_points"])
    m.azn_nodes = [dict(a) for a in snap["azn_nodes"]]
    m.injection_zones = [dict(z) for z in snap["injection_zones"]]
    # .get(): tolerate snapshots taken before hazards existed
    m.hazards = [{**hz, "path": list(hz["path"])} for hz in snap.get("hazards", [])]
