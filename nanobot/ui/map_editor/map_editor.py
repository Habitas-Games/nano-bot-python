"""Top-level map editor screen. Owns the document, undo history, file I/O,
renderer, sidebar, and the active tool, and routes pygame events to them —
the pygame equivalent of the Godot project's (post-v0.0.3-refactor)
map_editor.gd. Modal dialogs (load picker, save filename, messages) are
simple overlay states drawn on top of the canvas rather than separate
pygame windows, since pygame has no native dialog widgets."""

from __future__ import annotations

import glob
import os

import pygame

from nanobot.core import map_loader
from nanobot.core.map_data import Density, MapData, StreamDir
from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.map_canvas_renderer import CELL_SIZE, MapCanvasRenderer
from nanobot.ui.map_editor.map_editor_sidebar import MapEditorSidebar
from nanobot.ui.map_editor.map_history import MapHistory
from nanobot.ui.map_editor.tools.azn_tool import AznTool
from nanobot.ui.map_editor.tools.delete_tool import DeleteTool
from nanobot.ui.map_editor.tools.edit_tool import EditTool
from nanobot.ui.map_editor.tools.habitas_tool import HabitasTool
from nanobot.ui.map_editor.tools.pan_tool import PanTool
from nanobot.ui.map_editor.tools.stream_tool import StreamTool
from nanobot.ui.map_editor.tools.terrain_tool import TerrainTool
from nanobot.ui.map_editor.tools.zone_tool import ZoneTool
from nanobot.ui.widgets import Button, draw_text

MIN_ZOOM, MAX_ZOOM, ZOOM_STEP = 0.5, 3.0, 0.1
STATUS_BAR_HEIGHT = 26
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maps")


class MapEditorScreen:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.doc: MapData = ops.init_blank(60, 60)
        self.history = MapHistory()
        self.renderer = MapCanvasRenderer()
        self.sidebar = MapEditorSidebar(screen_size)

        self.zoom = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.canvas_rect = pygame.Rect(0, 0, 0, 0)
        self._recompute_canvas_rect()

        self.is_dragging = False
        self.brush_cursor_pos: tuple[int, int] = (-1, -1)
        self.last_paint_pos: tuple[int, int] = (-1, -1)
        self.selected_density = Density.LOW
        self.selected_stream_dir = StreamDir.NORTH
        self.edit_selected_type = ""
        self.edit_selected_index = -1
        self.zone_resize_corner = ""
        self.preview_rect: tuple[int, int, int, int] | None = None
        self.azn_hover_index = -1

        self.status_text = ""
        self.modal: dict | None = None

        self.tools = {
            "terrain": TerrainTool(self),
            "stream": StreamTool(self),
            "habitas": HabitasTool(self),
            "azn": AznTool(self),
            "zone": ZoneTool(self),
            "pan": PanTool(self),
            "edit": EditTool(self),
            "delete": DeleteTool(self),
        }
        self.active_tool_name = "terrain"
        self.current_tool = self.tools["terrain"]

        self.sidebar.on_density = self._on_density_selected
        self.sidebar.on_stream_dir = self._on_stream_selected
        self.sidebar.on_tool = self.activate_tool
        self.sidebar.on_load = self._open_load_picker
        self.sidebar.on_save = self._start_save_flow
        self.sidebar.on_clear = self._clear_map
        self.sidebar.on_undo = self._undo

        self._load_default_map()
        self.activate_tool("terrain")

    # --- layout ---

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self.sidebar.resize(screen_size)
        self._recompute_canvas_rect()

    def _recompute_canvas_rect(self) -> None:
        from nanobot.ui.map_editor.map_editor_sidebar import PANEL_WIDTH
        w = self.screen_size[0] - PANEL_WIDTH
        h = self.screen_size[1] - STATUS_BAR_HEIGHT
        self.canvas_rect = pygame.Rect(0, STATUS_BAR_HEIGHT, max(0, w), max(0, h))

    # --- tool activation ---

    def activate_tool(self, name: str) -> None:
        self.current_tool.on_deactivate()
        self.is_dragging = False
        self.brush_cursor_pos = (-1, -1)
        self.preview_rect = None
        self.active_tool_name = name
        self.current_tool = self.tools[name]
        self.current_tool.on_activate()
        self._update_status()

    def _on_density_selected(self, d: Density) -> None:
        self.selected_density = d
        self.activate_tool("terrain")

    def _on_stream_selected(self, sd: StreamDir) -> None:
        self.selected_stream_dir = sd
        self.activate_tool("stream")

    def _update_status(self) -> None:
        self.status_text = self.current_tool.get_status_text()

    # --- map load/save ---

    def _load_default_map(self) -> None:
        candidates = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        for path in candidates:
            if self._load_map_from_file(path):
                return
        self.doc = ops.init_blank(60, 60)
        self.history.reset()
        self.history.save_state(self.doc)
        self.sidebar.set_undo_enabled(self.history.can_undo())

    def _load_map_from_file(self, path: str) -> bool:
        loaded = map_loader.load_from_file(path)
        if loaded is None:
            self._show_message(f"Failed to load: {os.path.basename(path)}")
            return False
        self.doc = loaded
        self.zoom = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.history.reset()
        self.history.save_state(self.doc)
        self.sidebar.set_undo_enabled(self.history.can_undo())
        self.status_text = f"Loaded: {os.path.basename(path)}"
        return True

    def _open_load_picker(self) -> None:
        files = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if not files:
            self._show_message("No maps found in maps/")
            return
        self.modal = {"type": "load_picker", "files": files}

    def _start_save_flow(self) -> None:
        errors = map_loader.validate(self.doc)
        if errors:
            self.modal = {"type": "confirm_save_anyway", "errors": errors}
        else:
            self.modal = {"type": "save_filename", "buffer": "my_map.json"}

    def _do_save(self, filename: str) -> None:
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(MAPS_DIR, filename)
        if map_loader.save_to_file(self.doc, path):
            self.status_text = f"Saved: {filename}"
        else:
            self._show_message(f"Failed to save: {filename}")

    def _clear_map(self) -> None:
        self.history.save_state(self.doc)
        ops.clear_all(self.doc)
        self.sidebar.set_undo_enabled(self.history.can_undo())

    def _undo(self) -> None:
        self.history.undo(self.doc)
        self.sidebar.set_undo_enabled(self.history.can_undo())

    def _show_message(self, text: str) -> None:
        self.modal = {"type": "message", "text": text}

    # --- coordinate helpers ---

    def _to_grid_pos(self, screen_pos: tuple[int, int]) -> tuple[int, int]:
        size = CELL_SIZE * self.zoom
        gx = int((screen_pos[0] - self.canvas_rect.x + self.scroll_x) / size)
        gy = int((screen_pos[1] - self.canvas_rect.y + self.scroll_y) / size)
        return (gx, gy)

    def _is_in_canvas(self, pos: tuple[int, int]) -> bool:
        return self.canvas_rect.collidepoint(pos)

    # --- event handling ---

    def handle_event(self, event: "pygame.event.Event") -> None:
        if self.modal is not None:
            self._handle_modal_event(event)
            return

        if self.sidebar.handle_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if self.current_tool.handle_key(event):
                self._update_status()
                return

        if event.type == pygame.MOUSEWHEEL:
            if self._is_in_canvas(pygame.mouse.get_pos()):
                self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom + event.y * ZOOM_STEP))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and self._is_in_canvas(event.pos):
            grid_pos = self._to_grid_pos(event.pos)
            if self.current_tool.handle_press(grid_pos, event.button):
                if event.button == 1:
                    self.is_dragging = True
                self._update_status()
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_dragging:
            self.is_dragging = False
            self.current_tool.handle_release()
            return

        if event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                grid_pos = self._to_grid_pos(event.pos)
                self.current_tool.handle_drag(grid_pos, event.rel)
            else:
                pygame.mouse.set_cursor(self.current_tool.get_cursor())
                self._update_azn_hover(event.pos)

    def _update_azn_hover(self, screen_pos: tuple[int, int]) -> None:
        if not self._is_in_canvas(screen_pos):
            self.azn_hover_index = -1
            return
        grid_pos = self._to_grid_pos(screen_pos)
        if not self.doc.is_in_bounds(*grid_pos):
            self.azn_hover_index = -1
            return
        for i, azn in enumerate(self.doc.azn_nodes):
            if azn["position"] == grid_pos:
                self.azn_hover_index = i
                return
        self.azn_hover_index = -1

    # --- modal dialogs ---

    def _handle_modal_event(self, event: "pygame.event.Event") -> None:
        m = self.modal
        if m["type"] == "message":
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE)):
                self.modal = None
        elif m["type"] == "confirm_save_anyway":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.modal = {"type": "save_filename", "buffer": "my_map.json"}
                elif event.key == pygame.K_ESCAPE:
                    self.modal = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if getattr(self, "_modal_yes_rect", None) and self._modal_yes_rect.collidepoint(event.pos):
                    self.modal = {"type": "save_filename", "buffer": "my_map.json"}
                elif getattr(self, "_modal_no_rect", None) and self._modal_no_rect.collidepoint(event.pos):
                    self.modal = None
        elif m["type"] == "save_filename":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._do_save(m["buffer"])
                    self.modal = None
                elif event.key == pygame.K_ESCAPE:
                    self.modal = None
                elif event.key == pygame.K_BACKSPACE:
                    m["buffer"] = m["buffer"][:-1]
                elif event.unicode and event.unicode.isprintable():
                    m["buffer"] += event.unicode
        elif m["type"] == "load_picker":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.modal = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(getattr(self, "_modal_file_rects", [])):
                    if rect.collidepoint(event.pos):
                        self._load_map_from_file(m["files"][i])
                        self.modal = None
                        return
                if not getattr(self, "_modal_box_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                    self.modal = None

    # --- draw ---

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((30, 30, 30))

        selection = {"type": self.edit_selected_type, "index": self.edit_selected_index}
        self.renderer.draw_all(surface, self.doc, self.canvas_rect, self.zoom,
                                self.scroll_x, self.scroll_y, self.brush_cursor_pos,
                                selection, self.azn_hover_index, self.preview_rect)

        pygame.draw.rect(surface, (20, 20, 20), (0, 0, self.canvas_rect.width, STATUS_BAR_HEIGHT))
        draw_text(surface, self.status_text, (8, 6), size=12)

        self.sidebar.draw(surface)

        if self.modal is not None:
            self._draw_modal(surface)

    def _draw_modal(self, surface: "pygame.Surface") -> None:
        overlay = pygame.Surface(self.screen_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        m = self.modal
        box_w, box_h = 360, 160
        box_x = (self.screen_size[0] - box_w) // 2
        box_y = (self.screen_size[1] - box_h) // 2

        if m["type"] == "load_picker":
            box_h = 60 + 28 * len(m["files"])
            box_y = (self.screen_size[1] - box_h) // 2

        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        self._modal_box_rect = box_rect
        pygame.draw.rect(surface, (45, 48, 58), box_rect, border_radius=6)
        pygame.draw.rect(surface, (90, 95, 110), box_rect, width=2, border_radius=6)

        if m["type"] == "message":
            draw_text(surface, m["text"], (box_x + 16, box_y + 20), size=14)
            draw_text(surface, "(click or press Enter to dismiss)", (box_x + 16, box_y + box_h - 30), size=11, color=(150, 150, 150))

        elif m["type"] == "confirm_save_anyway":
            draw_text(surface, "Map incomplete:", (box_x + 16, box_y + 16), size=14)
            for i, err in enumerate(m["errors"]):
                draw_text(surface, f"- {err}", (box_x + 16, box_y + 40 + i * 18), size=12, color=(220, 180, 100))
            yes_rect = pygame.Rect(box_x + 16, box_y + box_h - 40, 100, 28)
            no_rect = pygame.Rect(box_x + box_w - 116, box_y + box_h - 40, 100, 28)
            self._modal_yes_rect = yes_rect
            self._modal_no_rect = no_rect
            Button(yes_rect, "Save Anyway").draw(surface)
            Button(no_rect, "Cancel").draw(surface)

        elif m["type"] == "save_filename":
            draw_text(surface, "Save map as:", (box_x + 16, box_y + 20), size=14)
            input_rect = pygame.Rect(box_x + 16, box_y + 50, box_w - 32, 28)
            pygame.draw.rect(surface, (20, 22, 30), input_rect)
            pygame.draw.rect(surface, (90, 95, 110), input_rect, width=1)
            draw_text(surface, m["buffer"] + "_", (input_rect.x + 6, input_rect.y + 6), size=13)
            draw_text(surface, "Saves into maps/. Enter to confirm, Esc to cancel.",
                      (box_x + 16, box_y + box_h - 26), size=11, color=(150, 150, 150))

        elif m["type"] == "load_picker":
            draw_text(surface, "Load map:", (box_x + 16, box_y + 16), size=14)
            rects = []
            for i, path in enumerate(m["files"]):
                r = pygame.Rect(box_x + 12, box_y + 44 + i * 28, box_w - 24, 24)
                hovered = r.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(surface, (60, 64, 78) if hovered else (38, 40, 50), r, border_radius=3)
                draw_text(surface, os.path.basename(path), (r.x + 8, r.y + 4), size=12)
                rects.append(r)
            self._modal_file_rects = rects
