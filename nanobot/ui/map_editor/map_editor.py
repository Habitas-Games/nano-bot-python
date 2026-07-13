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
from nanobot.ui import icons
from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.map_canvas_renderer import CELL_SIZE, MapCanvasRenderer
from nanobot.ui.map_editor.map_editor_sidebar import MapEditorSidebar
from nanobot.ui.map_editor.map_history import MapHistory
from nanobot.ui.map_editor.tools.azn_tool import AznTool
from nanobot.ui.map_editor.tools.delete_tool import DeleteTool
from nanobot.ui.map_editor.tools.edit_tool import EditTool
from nanobot.ui.map_editor.tools.habitas_tool import HabitasTool
from nanobot.ui.map_editor.tools.hazard_tool import HazardTool
from nanobot.ui.map_editor.tools.pan_tool import PanTool
from nanobot.ui.map_editor.tools.stream_tool import StreamTool
from nanobot.ui.map_editor.tools.terrain_tool import TerrainTool
from nanobot.ui.map_editor.tools.zone_tool import ZoneTool
from nanobot.ui.widgets import Button, draw_text, get_font

MIN_ZOOM, MAX_ZOOM, ZOOM_STEP = 0.5, 3.0, 0.1
STATUS_BAR_HEIGHT = 44
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maps")

# Tools that aren't "terrain" or "stream" (which get a live tile/stream
# texture preview instead — see _draw_active_tool_indicator) show one of
# these fixed icons.
_TOOL_ICON_FNS = {
    "pan": icons.pan_icon,
    "edit": icons.edit_icon,
    "delete": icons.delete_icon,
    "habitas": icons.habitas_icon,
    "azn": icons.azn_icon,
    "zone": icons.zone_icon,
    "hazard": icons.white_cell_icon,
}

# New Map size limits: below 10 nothing meaningful fits (two zones plus
# an objective); above 200 is the requirements' recommended maximum.
MIN_MAP_SIZE, MAX_MAP_SIZE = 10, 200

_cursor_setting_broken = False


def _set_cursor_safe(cursor: int) -> None:
    """pygame.mouse.set_cursor() can raise on environments without a real
    cursor theme/display (confirmed under SDL's dummy driver during
    headless testing; some minimal Linux window managers can hit this
    too). This fires on every mouse-move when not dragging, so a crash
    here would be frequent and severe — fail once, then silently stop
    trying rather than spamming exceptions or crashing the app."""
    global _cursor_setting_broken
    if _cursor_setting_broken:
        return
    try:
        pygame.mouse.set_cursor(cursor)
    except pygame.error:
        _cursor_setting_broken = True


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
        self.zone_player = 0  # owner (0-indexed) for newly placed injection zones
        self.edit_selected_type = ""
        self.edit_selected_index = -1
        self.zone_resize_corner = ""
        self.preview_rect: tuple[int, int, int, int] | None = None
        self.azn_hover_index = -1

        self.status_text = ""
        self.modal: dict | None = None
        self.on_back_to_menu = None  # callback(), set by main.py — see App._open_editor
        # Filename of the map currently being edited (basename, may be
        # None for a brand-new document) and the undo-stack position at
        # the last load/save — together they drive the save-as prefill,
        # the unsaved-changes marker, and the confirm-before-Load guard.
        self.current_filename: str | None = None
        self._saved_history_pos = 0

        self.menu_btn = Button((screen_size[0] - 110, 6, 100, 32), "Menu",
                                icon=icons.back_arrow_icon(16), on_click=self._fire_back_to_menu)

        self.tools = {
            "terrain": TerrainTool(self),
            "stream": StreamTool(self),
            "habitas": HabitasTool(self),
            "azn": AznTool(self),
            "zone": ZoneTool(self),
            "hazard": HazardTool(self),
            "pan": PanTool(self),
            "edit": EditTool(self),
            "delete": DeleteTool(self),
        }
        self.active_tool_name = "terrain"
        self.current_tool = self.tools["terrain"]

        self.sidebar.on_density = self._on_density_selected
        self.sidebar.on_stream_dir = self._on_stream_selected
        self.sidebar.on_tool = self.activate_tool
        self.sidebar.on_zone_player = self._set_zone_player
        self.sidebar.on_new = self._start_new_map_flow
        self.sidebar.on_load = self._open_load_picker
        self.sidebar.on_save = self._start_save_flow
        self.sidebar.on_clear = self._clear_map
        self.sidebar.on_undo = self._undo
        self.sidebar.on_redo = self._redo
        self.sidebar.on_azn_delta = self._change_starting_azn
        self.sidebar.on_bonus_delta = self._change_bonus

        self._load_default_map()
        self.activate_tool("terrain")

    # --- layout ---

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self.sidebar.resize(screen_size)
        self._recompute_canvas_rect()
        self.menu_btn.rect.x = screen_size[0] - 110

    def _set_zone_player(self, idx: int) -> None:
        self.zone_player = idx
        self._update_status()

    def _fire_back_to_menu(self) -> None:
        if self.on_back_to_menu:
            self.on_back_to_menu()

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
        self.sidebar.set_active_tool(name)
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
        self.current_filename = os.path.basename(path)
        self._saved_history_pos = self.history.position
        self.status_text = f"Loaded: {os.path.basename(path)}"
        return True

    def _is_dirty(self) -> bool:
        return self.history.position != self._saved_history_pos

    def _change_starting_azn(self, delta: int) -> None:
        new_value = max(0, min(995, self.doc.starting_azn + delta))
        if new_value == self.doc.starting_azn:
            return
        # A real document edit like any other: snapshotted (undoable) and
        # counted by the dirty tracker.
        self.history.save_state(self.doc)
        self.doc.starting_azn = new_value
        self.status_text = f"Starting AZN: {new_value}"

    def _change_bonus(self, delta: int) -> None:
        new_value = max(0, min(500, self.doc.bonus_hold_all + delta))
        if new_value == self.doc.bonus_hold_all:
            return
        self.history.save_state(self.doc)
        self.doc.bonus_hold_all = new_value
        self.status_text = (f"Hold-all bonus: +{new_value}/turn while one player holds every Habitas Point"
                            if new_value else "Hold-all bonus: off")

    def _start_new_map_flow(self) -> None:
        if self._is_dirty():
            self.modal = {"type": "confirm_discard", "next": "new"}
            return
        self.modal = {"type": "new_map", "buffer": "60x60"}

    def _create_new_map(self, spec: str) -> None:
        try:
            w_str, h_str = spec.lower().replace(" ", "").split("x")
            w, h = int(w_str), int(h_str)
        except ValueError:
            self._show_message(f"Size must look like 60x60 (got: {spec})")
            return
        w = max(MIN_MAP_SIZE, min(MAX_MAP_SIZE, w))
        h = max(MIN_MAP_SIZE, min(MAX_MAP_SIZE, h))
        self.doc = ops.init_blank(w, h)
        self.zoom = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.current_filename = None
        self.history.reset()
        self.history.save_state(self.doc)
        self._saved_history_pos = self.history.position
        self.sidebar.set_undo_enabled(self.history.can_undo())
        self.status_text = f"New blank map: {w}x{h}"

    def _open_load_picker(self) -> None:
        # Loading replaces the document outright — with unsaved edits in
        # flight, ask first instead of silently discarding them.
        if self._is_dirty():
            self.modal = {"type": "confirm_discard", "next": "load"}
            return
        self._open_load_picker_now()

    def _open_load_picker_now(self) -> None:
        files = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if not files:
            self._show_message("No maps found in maps/")
            return
        self.modal = {"type": "load_picker", "files": files}

    def _save_buffer_default(self) -> str:
        # Prefill with the file being edited — re-saving vascular_network
        # used to suggest "my_map.json" and make you retype the real name.
        return self.current_filename or "my_map.json"

    def _start_save_flow(self) -> None:
        errors = map_loader.validate(self.doc)
        if errors:
            self.modal = {"type": "confirm_save_anyway", "errors": errors}
        else:
            self.modal = {"type": "save_filename", "buffer": self._save_buffer_default()}

    def _do_save(self, filename: str) -> None:
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(MAPS_DIR, filename)
        # The display name doubles as the replay->map resolution key, so
        # stamp it from the filename on every save — new maps used to all
        # save as "Untitled Map", which made their replays ambiguous.
        self.doc.map_name = map_loader.derive_map_name(filename)
        if map_loader.save_to_file(self.doc, path):
            self.current_filename = filename
            self._saved_history_pos = self.history.position
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

    def _redo(self) -> None:
        self.history.redo(self.doc)
        self.sidebar.set_undo_enabled(self.history.can_undo())

    def _show_message(self, text: str) -> None:
        self.modal = {"type": "message", "text": text}

    # --- coordinate helpers ---

    def _clamp_scroll(self) -> None:
        max_x = max(0, int(self.doc.width * CELL_SIZE * self.zoom - self.canvas_rect.width))
        max_y = max(0, int(self.doc.height * CELL_SIZE * self.zoom - self.canvas_rect.height))
        self.scroll_x = max(0, min(self.scroll_x, max_x))
        self.scroll_y = max(0, min(self.scroll_y, max_y))

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

        if self.menu_btn.handle_event(event):
            return

        if self.sidebar.handle_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.mod & pygame.KMOD_CTRL:
                if event.key == pygame.K_z and (event.mod & pygame.KMOD_SHIFT):
                    self._redo()
                    return
                if event.key == pygame.K_z:
                    self._undo()
                    return
                if event.key == pygame.K_y:
                    self._redo()
                    return
                if event.key == pygame.K_s:
                    self._start_save_flow()
                    return
            if self.current_tool.handle_key(event):
                self._update_status()
                return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._is_in_canvas((mx, my)):
                # Anchored at the cursor (same fix as the playback viewer):
                # the cell under the mouse stays put while zooming, instead
                # of the view sliding toward the map's top-left corner.
                old = self.zoom
                self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, old + event.y * ZOOM_STEP))
                if self.zoom != old:
                    wx = (mx - self.canvas_rect.x + self.scroll_x) / old
                    wy = (my - self.canvas_rect.y + self.scroll_y) / old
                    self.scroll_x = int(wx * self.zoom - (mx - self.canvas_rect.x))
                    self.scroll_y = int(wy * self.zoom - (my - self.canvas_rect.y))
                    self._clamp_scroll()
            return

        # Middle-drag pans from any tool — switching to the Pan tool just
        # to reposition and back again was the single most repetitive
        # round-trip in editing sessions. getattr because synthetic events
        # (tests/check_editor.py) may omit the buttons tuple.
        if event.type == pygame.MOUSEMOTION and getattr(event, "buttons", (0, 0, 0))[1]:
            self.scroll_x -= event.rel[0]
            self.scroll_y -= event.rel[1]
            self._clamp_scroll()
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
                _set_cursor_safe(self.current_tool.get_cursor())
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
                    self.modal = {"type": "save_filename", "buffer": self._save_buffer_default()}
                elif event.key == pygame.K_ESCAPE:
                    self.modal = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if getattr(self, "_modal_yes_rect", None) and self._modal_yes_rect.collidepoint(event.pos):
                    self.modal = {"type": "save_filename", "buffer": self._save_buffer_default()}
                elif getattr(self, "_modal_no_rect", None) and self._modal_no_rect.collidepoint(event.pos):
                    self.modal = None
        elif m["type"] == "confirm_discard":
            def proceed():
                nxt = m.get("next", "load")
                self.modal = None
                if nxt == "new":
                    self.modal = {"type": "new_map", "buffer": "60x60"}
                else:
                    self._open_load_picker_now()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    proceed()
                elif event.key == pygame.K_ESCAPE:
                    self.modal = None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if getattr(self, "_modal_yes_rect", None) and self._modal_yes_rect.collidepoint(event.pos):
                    proceed()
                elif getattr(self, "_modal_no_rect", None) and self._modal_no_rect.collidepoint(event.pos):
                    self.modal = None
        elif m["type"] == "new_map":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    spec = m["buffer"]
                    self.modal = None
                    self._create_new_map(spec)
                elif event.key == pygame.K_ESCAPE:
                    self.modal = None
                elif event.key == pygame.K_BACKSPACE:
                    m["buffer"] = m["buffer"][:-1]
                elif event.unicode and (event.unicode.isdigit() or event.unicode.lower() == "x"):
                    if len(m["buffer"]) < 8:
                        m["buffer"] += event.unicode.lower()
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
        pending_hazard = self.tools["hazard"].pending if self.active_tool_name == "hazard" else None
        self.renderer.draw_all(surface, self.doc, self.canvas_rect, self.zoom,
                                self.scroll_x, self.scroll_y, self.brush_cursor_pos,
                                selection, self.azn_hover_index, self.preview_rect,
                                pending_hazard=pending_hazard)

        self._draw_top_bar(surface)
        # Synced every frame rather than at call sites: every tool pushes
        # undo states (history.save_state) but none of them notified the
        # sidebar, so the Undo button stayed greyed out after the first
        # paint until some unrelated action (Load/Clear) refreshed it —
        # found via the v0.0.15 QA screenshots.
        self.sidebar.set_undo_enabled(self.history.can_undo())
        self.sidebar.set_redo_enabled(self.history.can_redo())
        # Same per-frame sync: undo can also change starting_azn/bonus.
        self.sidebar.set_starting_azn(self.doc.starting_azn)
        self.sidebar.set_bonus(self.doc.bonus_hold_all)
        self.sidebar.draw(surface)

        # Drawn last, after the sidebar, so it's never painted over —
        # confirmed this was a real bug: the sidebar is drawn after the top
        # bar and is fully opaque, so a button positioned at the screen's
        # right edge (sitting above the sidebar, matching where the
        # playback viewer and tournament screen put their own back
        # buttons) was being completely hidden underneath it.
        self.menu_btn.draw(surface)

        if self.modal is not None:
            self._draw_modal(surface)

    def _draw_top_bar(self, surface: "pygame.Surface") -> None:
        pygame.draw.rect(surface, (20, 20, 20), (0, 0, self.canvas_rect.width, STATUS_BAR_HEIGHT))

        # The active tool/tile indicator: what you click will paint *this*,
        # shown as the real texture for Terrain/Stream (not just a color
        # swatch) and as the matching icon for every other tool, so the
        # current state is glanceable at the top instead of only visible
        # as a highlighted button somewhere in the sidebar.
        icon_box = pygame.Rect(8, 6, 32, 32)
        pygame.draw.rect(surface, (45, 48, 58), icon_box, border_radius=4)
        pygame.draw.rect(surface, (80, 84, 96), icon_box, width=1, border_radius=4)

        if self.active_tool_name == "terrain":
            tex = self.renderer.terrain_textures.get(self.selected_density)
            if tex:
                surface.blit(pygame.transform.smoothscale(tex, (28, 28)), (icon_box.x + 2, icon_box.y + 2))
        elif self.active_tool_name == "stream":
            preview_rect = pygame.Rect(icon_box.x + 2, icon_box.y + 2, 28, 28)
            self.renderer._draw_stream_cell(surface, preview_rect, self.selected_stream_dir)
        else:
            icon_fn = _TOOL_ICON_FNS.get(self.active_tool_name)
            if icon_fn:
                surface.blit(icon_fn(28), (icon_box.x + 2, icon_box.y + 2))

        # Right side of the top bar: which file is being edited, with an
        # unsaved-changes dot — before this there was no on-screen record
        # of what you had loaded or whether your work was saved.
        name = self.current_filename or "(new map)"
        if self._is_dirty():
            name += "  * unsaved"
        label = get_font(12).render(name, True, (220, 190, 120) if self._is_dirty() else (150, 155, 168))
        label_x = self.canvas_rect.width - label.get_width() - 12
        surface.blit(label, (label_x, 16))

        # Status text truncates to the space before the filename — at the
        # minimum window width, the hazard tool's (long) status line used
        # to overprint the filename (verified by screenshot in v0.0.20's
        # review pass).
        font12 = get_font(12)
        status = self.status_text
        max_w = label_x - (icon_box.right + 10) - 16
        if font12.size(status)[0] > max_w:
            while status and font12.size(status + "...")[0] > max_w:
                status = status[:-1]
            status += "..."
        draw_text(surface, status, (icon_box.right + 10, 16), size=12)

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

        elif m["type"] == "confirm_discard":
            name = self.current_filename or "this map"
            draw_text(surface, f"Discard unsaved changes to {name}?", (box_x + 16, box_y + 20), size=14)
            draw_text(surface, "Loading another map replaces your edits.", (box_x + 16, box_y + 46),
                      size=12, color=(220, 180, 100))
            yes_rect = pygame.Rect(box_x + 16, box_y + box_h - 40, 100, 28)
            no_rect = pygame.Rect(box_x + box_w - 116, box_y + box_h - 40, 100, 28)
            self._modal_yes_rect = yes_rect
            self._modal_no_rect = no_rect
            Button(yes_rect, "Discard").draw(surface)
            Button(no_rect, "Cancel").draw(surface)

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

        elif m["type"] == "new_map":
            draw_text(surface, "New map size (width x height):", (box_x + 16, box_y + 20), size=14)
            input_rect = pygame.Rect(box_x + 16, box_y + 50, box_w - 32, 28)
            pygame.draw.rect(surface, (20, 22, 30), input_rect)
            pygame.draw.rect(surface, (90, 95, 110), input_rect, width=1)
            draw_text(surface, m["buffer"] + "_", (input_rect.x + 6, input_rect.y + 6), size=13)
            draw_text(surface, f"{MIN_MAP_SIZE}-{MAX_MAP_SIZE} per side. Enter to create, Esc to cancel.",
                      (box_x + 16, box_y + box_h - 26), size=11, color=(150, 150, 150))

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
