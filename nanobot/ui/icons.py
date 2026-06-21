"""Small vector-drawn icons for tool buttons. pygame has no built-in icon
set and the project has no icon asset files, so these are drawn with
plain pygame.draw primitives once and cached as small Surfaces — cheap,
no new asset files, and trivial to recolor for the active/hover states
buttons already need.

Each draw_*_icon(size, color) returns a pygame.Surface sized
(size, size) with per-pixel alpha, ready to hand to Button(icon=...).
"""

from __future__ import annotations

import math

import pygame

_cache: dict[tuple, "pygame.Surface"] = {}


def _surface(size: int) -> "pygame.Surface":
    return pygame.Surface((size, size), pygame.SRCALPHA)


def pan_icon(size: int = 28, color=(220, 220, 220)) -> "pygame.Surface":
    """Four arrows pointing outward from a center point — the universal
    'move/pan' glyph."""
    key = ("pan", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    c = size / 2
    arm = size * 0.36
    head = size * 0.13
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        tip = (c + dx * arm, c + dy * arm)
        base = (c + dx * (arm - head), c + dy * (arm - head))
        pygame.draw.line(s, color, (c, c), base, 2)
        perp = (-dy, dx)
        p1 = (tip[0], tip[1])
        p2 = (base[0] + perp[0] * head * 0.7, base[1] + perp[1] * head * 0.7)
        p3 = (base[0] - perp[0] * head * 0.7, base[1] - perp[1] * head * 0.7)
        pygame.draw.polygon(s, color, [p1, p2, p3])
    pygame.draw.circle(s, color, (c, c), 2)
    _cache[key] = s
    return s


def edit_icon(size: int = 28, color=(220, 220, 220)) -> "pygame.Surface":
    """A pencil: a slanted body with a triangular tip."""
    key = ("edit", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    x0, y0 = size * 0.22, size * 0.78
    x1, y1 = size * 0.72, size * 0.22
    width = size * 0.12
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * width, dx / length * width
    body = [
        (x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny), (x0 - nx, y0 - ny),
    ]
    pygame.draw.polygon(s, color, body)
    tip_len = size * 0.16
    tx, ty = x0 - dx / length * tip_len, y0 - dy / length * tip_len
    pygame.draw.polygon(s, color, [(x0 + nx, y0 + ny), (x0 - nx, y0 - ny), (tx, ty)])
    _cache[key] = s
    return s


def delete_icon(size: int = 28, color=(220, 220, 220)) -> "pygame.Surface":
    """A trash can: lid + tapered body + slats."""
    key = ("delete", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    body_top = size * 0.32
    body_bottom = size * 0.85
    left_top, right_top = size * 0.28, size * 0.72
    left_bottom, right_bottom = size * 0.32, size * 0.68
    pygame.draw.polygon(s, color, [
        (left_top, body_top), (right_top, body_top),
        (right_bottom, body_bottom), (left_bottom, body_bottom),
    ], width=2)
    pygame.draw.line(s, color, (size * 0.20, body_top), (size * 0.80, body_top), 2)
    pygame.draw.line(s, color, (size * 0.40, body_top), (size * 0.40, size * 0.20), 2)
    pygame.draw.line(s, color, (size * 0.60, body_top), (size * 0.60, size * 0.20), 2)
    pygame.draw.line(s, color, (size * 0.40, size * 0.20), (size * 0.60, size * 0.20), 2)
    for fx in (0.42, 0.5, 0.58):
        pygame.draw.line(s, color, (size * fx, body_top + 3), (size * fx, body_bottom - 3), 1)
    _cache[key] = s
    return s


def habitas_icon(size: int = 28, color=(230, 200, 90)) -> "pygame.Surface":
    """A map-pin marker — matches what's actually placed on the map."""
    key = ("habitas", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    cx, top, r = size / 2, size * 0.18, size * 0.26
    cy = top + r
    tip = (cx, size * 0.85)
    pygame.draw.circle(s, color, (cx, cy), r)
    pygame.draw.polygon(s, color, [
        (cx - r * 0.7, cy + r * 0.55), (cx + r * 0.7, cy + r * 0.55), tip,
    ])
    pygame.draw.circle(s, (30, 30, 30), (cx, cy), r * 0.4)
    _cache[key] = s
    return s


def azn_icon(size: int = 28, color=(230, 200, 60)) -> "pygame.Surface":
    """A diamond/gem — the resource-node glyph."""
    key = ("azn", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    cx, cy, r = size / 2, size / 2, size * 0.32
    pygame.draw.polygon(s, color, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])
    pygame.draw.polygon(s, color, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], width=2)
    _cache[key] = s
    return s


def zone_icon(size: int = 28, color=(120, 170, 230)) -> "pygame.Surface":
    """A dashed rectangle outline — placing a zone."""
    key = ("zone", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    rect = pygame.Rect(size * 0.18, size * 0.22, size * 0.64, size * 0.56)
    dash = 4
    x0, y0, x1, y1 = rect.left, rect.top, rect.right, rect.bottom
    for edge_start, edge_end in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                                  ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        length = math.hypot(edge_end[0] - edge_start[0], edge_end[1] - edge_start[1])
        steps = max(1, int(length // (dash * 2)))
        for i in range(steps + 1):
            t0 = (i * 2 * dash) / length
            t1 = min(1.0, (i * 2 * dash + dash) / length)
            p0 = (edge_start[0] + (edge_end[0] - edge_start[0]) * t0,
                  edge_start[1] + (edge_end[1] - edge_start[1]) * t0)
            p1 = (edge_start[0] + (edge_end[0] - edge_start[0]) * t1,
                  edge_start[1] + (edge_end[1] - edge_start[1]) * t1)
            pygame.draw.line(s, color, p0, p1, 2)
    _cache[key] = s
    return s


def play_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("play", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    pygame.draw.polygon(s, color, [
        (size * 0.28, size * 0.20), (size * 0.28, size * 0.80), (size * 0.82, size * 0.5),
    ])
    _cache[key] = s
    return s


def pause_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("pause", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    w = size * 0.18
    pygame.draw.rect(s, color, (size * 0.26, size * 0.2, w, size * 0.6))
    pygame.draw.rect(s, color, (size * 0.56, size * 0.2, w, size * 0.6))
    _cache[key] = s
    return s


def step_back_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("step_back", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    pygame.draw.rect(s, color, (size * 0.20, size * 0.22, size * 0.1, size * 0.56))
    pygame.draw.polygon(s, color, [
        (size * 0.80, size * 0.22), (size * 0.80, size * 0.78), (size * 0.32, size * 0.5),
    ])
    _cache[key] = s
    return s


def step_forward_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("step_forward", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    pygame.draw.rect(s, color, (size * 0.70, size * 0.22, size * 0.1, size * 0.56))
    pygame.draw.polygon(s, color, [
        (size * 0.20, size * 0.22), (size * 0.20, size * 0.78), (size * 0.68, size * 0.5),
    ])
    _cache[key] = s
    return s


def speed_down_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("speed_down", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    pygame.draw.line(s, color, (size * 0.22, size * 0.5), (size * 0.78, size * 0.5), 3)
    _cache[key] = s
    return s


def speed_up_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    key = ("speed_up", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    pygame.draw.line(s, color, (size * 0.22, size * 0.5), (size * 0.78, size * 0.5), 3)
    pygame.draw.line(s, color, (size * 0.5, size * 0.22), (size * 0.5, size * 0.78), 3)
    _cache[key] = s
    return s


def back_arrow_icon(size: int = 24, color=(220, 220, 220)) -> "pygame.Surface":
    """A leftward arrow — used alongside the 'Menu'/'Back' text label
    rather than alone, since a bare arrow can be ambiguous about what it
    does (back in history? collapse a panel?) without the word next to it."""
    key = ("back_arrow", size, color)
    if key in _cache:
        return _cache[key]
    s = _surface(size)
    cy = size / 2
    pygame.draw.line(s, color, (size * 0.68, cy), (size * 0.28, cy), 3)
    pygame.draw.line(s, color, (size * 0.28, cy), (size * 0.5, size * 0.28), 3)
    pygame.draw.line(s, color, (size * 0.28, cy), (size * 0.5, size * 0.72), 3)
    _cache[key] = s
    return s
