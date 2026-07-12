"""All drawing for the map editor canvas. Pygame port of the Godot
project's map_canvas_renderer.gd (see nano-bot's v0.0.3 refactor) — same
responsibilities, same draw order, same selection-highlight colors."""

from __future__ import annotations

import math
import os

import pygame

from nanobot.core.map_data import Density, MapData, StreamDir
from nanobot.ui.widgets import get_font

CELL_SIZE = 16
STREAM_COLOR = (179, 64, 64)
# A flat opaque black grid read as graph paper laid over the tissue
# rather than texture seams within it — softened to a translucent, warm
# dark tone so it still marks cell boundaries (needed for precise
# editing) without fighting the tissue palette's reds/greens/purples.
GRID_COLOR = (25, 12, 12, 70)
BRUSH_COLOR = (255, 255, 255)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")


def _load(rel_path: str) -> "pygame.Surface | None":
    path = os.path.join(ASSETS_DIR, rel_path)
    if not os.path.exists(path):
        return None
    return pygame.image.load(path).convert_alpha()


class MapCanvasRenderer:
    def __init__(self):
        self.terrain_textures = {
            Density.LOW: _load("tiles/tile_low.png"),
            Density.MEDIUM: _load("tiles/tile_medium.png"),
            Density.HIGH: _load("tiles/tile_high.png"),
            Density.BONE: _load("tiles/tile_bone.png"),
        }
        self.stream_h_texture = _load("tiles/tile_stream_h.png")
        self.stream_v_texture = _load("tiles/tile_stream_v.png")
        self.habitas_texture = _load("markers/habitas_neutral.png")
        self.azn_texture = _load("markers/azn_node.png")
        self._scaled_cache: dict[tuple[int, int], "pygame.Surface"] = {}

    def _scaled(self, tex: "pygame.Surface", size: int) -> "pygame.Surface":
        key = (id(tex), size)
        cached = self._scaled_cache.get(key)
        if cached is None or cached.get_width() != size:
            cached = pygame.transform.smoothscale(tex, (size, size))
            self._scaled_cache[key] = cached
        return cached

    def draw_all(self, surface: "pygame.Surface", m: MapData, canvas_rect: pygame.Rect,
                  zoom: float, scroll_x: int, scroll_y: int, brush_cursor_pos: tuple[int, int],
                  selection: dict, azn_hover_index: int,
                  preview_rect: tuple[int, int, int, int] | None = None,
                  pending_hazard: list[tuple[int, int]] | None = None) -> None:
        pygame.draw.rect(surface, (51, 51, 51), canvas_rect)
        prev_clip = surface.get_clip()
        surface.set_clip(canvas_rect)

        self._draw_cells(surface, m, canvas_rect, zoom, scroll_x, scroll_y, brush_cursor_pos)
        self._draw_zones(surface, m, canvas_rect, zoom, scroll_x, scroll_y, selection)
        self._draw_habitas(surface, m, canvas_rect, zoom, scroll_x, scroll_y, selection)
        self._draw_azn(surface, m, canvas_rect, zoom, scroll_x, scroll_y, selection, azn_hover_index)
        self._draw_hazards(surface, m, canvas_rect, zoom, scroll_x, scroll_y)
        if pending_hazard:
            self._draw_pending_hazard(surface, pending_hazard, canvas_rect, zoom, scroll_x, scroll_y)
        if preview_rect:
            self._draw_preview_rect(surface, preview_rect, canvas_rect, zoom, scroll_x, scroll_y)

        surface.set_clip(prev_clip)

    def _cell_screen_rect(self, x: int, y: int, canvas_rect: pygame.Rect,
                           zoom: float, scroll_x: int, scroll_y: int) -> pygame.Rect:
        size = CELL_SIZE * zoom
        sx = canvas_rect.x + x * size - scroll_x
        sy = canvas_rect.y + y * size - scroll_y
        return pygame.Rect(int(sx), int(sy), math.ceil(size), math.ceil(size))

    def _draw_cells(self, surface, m: MapData, canvas_rect, zoom, scroll_x, scroll_y, brush_cursor_pos) -> None:
        # Grid lines are drawn onto a separate SRCALPHA overlay and blitted
        # once at the end, rather than via pygame.draw.rect(..., GRID_COLOR)
        # directly on the main surface per cell — confirmed pygame.draw.rect
        # ignores the alpha channel and draws fully opaque on a surface
        # without its own per-pixel alpha, so a translucent grid color was
        # silently being drawn as flat opaque instead, however dark the RGB
        # happened to be. One shared overlay also avoids 6,400+ individual
        # alpha-surface allocations for an 80x80 map.
        grid_overlay = pygame.Surface(canvas_rect.size, pygame.SRCALPHA)

        for y in range(m.height):
            for x in range(m.width):
                cell = m._cells[y * m.width + x]
                r = self._cell_screen_rect(x, y, canvas_rect, zoom, scroll_x, scroll_y)
                if r.right < canvas_rect.left or r.left > canvas_rect.right:
                    continue
                if r.bottom < canvas_rect.top or r.top > canvas_rect.bottom:
                    continue

                if cell["stream_dir"] == StreamDir.NONE:
                    tex = self.terrain_textures.get(cell["density"])
                    if tex:
                        surface.blit(self._scaled(tex, r.width), r.topleft)
                    else:
                        pygame.draw.rect(surface, (128, 128, 128), r)
                else:
                    self._draw_stream_cell(surface, r, cell["stream_dir"])

                if (x, y) == tuple(brush_cursor_pos):
                    pygame.draw.rect(surface, BRUSH_COLOR, r, width=2)

                overlay_r = pygame.Rect(r.x - canvas_rect.x, r.y - canvas_rect.y, r.width, r.height)
                pygame.draw.rect(grid_overlay, GRID_COLOR, overlay_r, width=1)

        surface.blit(grid_overlay, canvas_rect.topleft)

    def _draw_stream_cell(self, surface, r: pygame.Rect, stream_dir: StreamDir) -> None:
        if stream_dir in (StreamDir.EAST, StreamDir.WEST):
            tex = self.stream_h_texture
            if tex:
                scaled = self._scaled(tex, r.width)
                if stream_dir == StreamDir.WEST:
                    scaled = pygame.transform.flip(scaled, True, False)
                surface.blit(scaled, r.topleft)
            else:
                pygame.draw.rect(surface, (102, 51, 51), r)
        else:
            tex = self.stream_v_texture
            if tex:
                scaled = self._scaled(tex, r.width)
                if stream_dir == StreamDir.NORTH:
                    scaled = pygame.transform.flip(scaled, False, True)
                surface.blit(scaled, r.topleft)
            else:
                pygame.draw.rect(surface, (102, 51, 51), r)

        center = pygame.Vector2(r.center)
        direction = _stream_to_vec(stream_dir)
        arrow_length = r.width * 0.5 - 3.5

        base = center - direction * arrow_length * 0.5
        tip = center + direction * arrow_length
        pygame.draw.line(surface, STREAM_COLOR, base, tip, 2)

        perp = pygame.Vector2(-direction.y, direction.x) * 2.5
        head_base = tip - direction * 3.5
        pygame.draw.line(surface, STREAM_COLOR, tip, head_base + perp, 2)
        pygame.draw.line(surface, STREAM_COLOR, tip, head_base - perp, 2)

    def _draw_zones(self, surface, m: MapData, canvas_rect, zoom, scroll_x, scroll_y, selection) -> None:
        for i, zone in enumerate(m.injection_zones):
            rx, ry, rw, rh = zone["rect"]
            tl = self._cell_screen_rect(rx, ry, canvas_rect, zoom, scroll_x, scroll_y)
            br = self._cell_screen_rect(rx + rw - 1, ry + rh - 1, canvas_rect, zoom, scroll_x, scroll_y)
            rect = pygame.Rect(tl.left, tl.top, br.right - tl.left, br.bottom - tl.top)

            color = (64, 140, 255) if zone["player"] == 0 else (255, 77, 64)
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((*color, 50))
            surface.blit(overlay, rect.topleft)

            if selection.get("type") == "zone" and selection.get("index") == i:
                hl = pygame.Surface(rect.size, pygame.SRCALPHA)
                hl.fill((255, 255, 255, 76))
                surface.blit(hl, rect.topleft)

                handle = 8
                for corner in (rect.topleft, rect.topright, rect.bottomleft, rect.bottomright):
                    pygame.draw.rect(surface, (255, 255, 0),
                                      pygame.Rect(corner[0] - handle // 2, corner[1] - handle // 2, handle, handle))

    def _draw_habitas(self, surface, m: MapData, canvas_rect, zoom, scroll_x, scroll_y, selection) -> None:
        for i, hp in enumerate(m.habitas_points):
            r = self._cell_screen_rect(hp[0], hp[1], canvas_rect, zoom, scroll_x, scroll_y)
            if self.habitas_texture:
                surface.blit(self._scaled(self.habitas_texture, r.width), r.topleft)
            if selection.get("type") == "habitas" and selection.get("index") == i:
                hl = pygame.Surface(r.size, pygame.SRCALPHA)
                hl.fill((255, 255, 0, 102))
                surface.blit(hl, r.topleft)

    def _draw_azn(self, surface, m: MapData, canvas_rect, zoom, scroll_x, scroll_y, selection, azn_hover_index) -> None:
        for i, azn in enumerate(m.azn_nodes):
            pos = azn["position"]
            r = self._cell_screen_rect(pos[0], pos[1], canvas_rect, zoom, scroll_x, scroll_y)
            if self.azn_texture:
                surface.blit(self._scaled(self.azn_texture, r.width), r.topleft)
            if selection.get("type") == "azn" and selection.get("index") == i:
                hl = pygame.Surface(r.size, pygame.SRCALPHA)
                hl.fill((255, 255, 0, 102))
                surface.blit(hl, r.topleft)

        if 0 <= azn_hover_index < len(m.azn_nodes):
            azn = m.azn_nodes[azn_hover_index]
            r = self._cell_screen_rect(azn["position"][0], azn["position"][1], canvas_rect, zoom, scroll_x, scroll_y)
            font = get_font(12)
            label = font.render(str(azn["quantity"]), True, (255, 255, 255))
            surface.blit(label, label.get_rect(center=(r.centerx, r.top - 10)))

    def _draw_hazards(self, surface, m: MapData, canvas_rect, zoom, scroll_x, scroll_y) -> None:
        """White-cell hazards: patrol path as a faint dashed-ish polyline,
        plus a pale blob at the start point. The editor has no hazard tool
        yet (they're authored in the map JSON), but a creator loading a
        hazard-bearing map must be able to see where they patrol — invisible
        hazards that silently round-trip through save would be a trap."""
        for hz in m.hazards:
            pts = [self._cell_screen_rect(p[0], p[1], canvas_rect, zoom, scroll_x, scroll_y).center
                   for p in hz["path"]]
            if len(pts) > 1:
                pygame.draw.lines(surface, (225, 228, 244), False, pts, 1)
            r = self._cell_screen_rect(hz["path"][0][0], hz["path"][0][1], canvas_rect, zoom, scroll_x, scroll_y)
            pygame.draw.circle(surface, (238, 240, 248), r.center, max(4, r.width // 2 - 1))
            pygame.draw.circle(surface, (160, 168, 205), r.center, max(2, r.width // 4))

    def _draw_pending_hazard(self, surface, path: list[tuple[int, int]],
                              canvas_rect, zoom, scroll_x, scroll_y) -> None:
        """The patrol being authored right now (hazard tool): green while
        under construction to distinguish it from committed patrols'
        white, with numbered waypoints so the loop order is unambiguous."""
        pts = [self._cell_screen_rect(p[0], p[1], canvas_rect, zoom, scroll_x, scroll_y).center
               for p in path]
        if len(pts) > 1:
            pygame.draw.lines(surface, (120, 220, 140), False, pts, 2)
        font = get_font(11)
        for i, pt in enumerate(pts):
            pygame.draw.circle(surface, (120, 220, 140), pt, 6)
            pygame.draw.circle(surface, (25, 60, 32), pt, 6, width=1)
            label = font.render(str(i + 1), True, (15, 30, 18))
            surface.blit(label, label.get_rect(center=pt))

    def _draw_preview_rect(self, surface, preview_rect, canvas_rect, zoom, scroll_x, scroll_y) -> None:
        rx, ry, rw, rh = preview_rect
        if rw <= 0 or rh <= 0:
            return
        tl = self._cell_screen_rect(rx, ry, canvas_rect, zoom, scroll_x, scroll_y)
        br = self._cell_screen_rect(rx + rw - 1, ry + rh - 1, canvas_rect, zoom, scroll_x, scroll_y)
        rect = pygame.Rect(tl.left, tl.top, br.right - tl.left, br.bottom - tl.top)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 38))
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), rect, width=2)


def _stream_to_vec(direction: StreamDir) -> "pygame.Vector2":
    return {
        StreamDir.NORTH: pygame.Vector2(0, -1),
        StreamDir.SOUTH: pygame.Vector2(0, 1),
        StreamDir.EAST: pygame.Vector2(1, 0),
        StreamDir.WEST: pygame.Vector2(-1, 0),
    }.get(direction, pygame.Vector2(0, 0))
