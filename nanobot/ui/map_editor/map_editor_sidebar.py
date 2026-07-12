"""Right-hand control panel for the map editor. Builds Button widgets and
exposes user intent through plain callback attributes (on_density,
on_stream_dir, on_tool, on_load, on_save, on_clear, on_undo) — the pygame
equivalent of the Godot sidebar's Signals."""

from __future__ import annotations

import pygame

from nanobot.core.map_data import Density, StreamDir
from nanobot.ui import icons
from nanobot.ui.widgets import Button, ButtonGroup, draw_hover_tooltips, draw_text, get_font

PANEL_WIDTH = 250
PADDING = 10
ROW_HEIGHT = 30


class MapEditorSidebar:
    def __init__(self, screen_size: tuple[int, int]):
        screen_width, screen_height = screen_size
        self.rect = pygame.Rect(screen_width - PANEL_WIDTH, 0, PANEL_WIDTH, screen_height)

        self.on_density = None       # callback(Density)
        self.on_stream_dir = None    # callback(StreamDir)
        self.on_tool = None          # callback(str)
        self.on_zone_player = None   # callback(int) — 0-indexed owner for new zones
        self.on_new = None
        self.on_load = None
        self.on_save = None
        self.on_clear = None
        self.on_undo = None
        self.on_redo = None
        self.on_azn_delta = None     # callback(int) — +/- step for starting AZN

        self._starting_azn_display = 150

        self.terrain_group = ButtonGroup()
        self.stream_group = ButtonGroup()
        self.zone_player_group = ButtonGroup()
        self.tool_group = ButtonGroup()  # Habitas/AZN/Zone/Pan/Edit/Delete — mutually exclusive, tracks active_tool_name
        self._tool_buttons_by_name: dict[str, Button] = {}
        self.undo_btn: Button | None = None
        self._action_buttons: list[Button] = []

        # Header y-positions, recorded while _build() lays out the actual
        # buttons rather than recomputed by hand in draw() from a parallel
        # set of arithmetic — those two used to drift out of sync the
        # moment either one changed without the other being updated too.
        self._headers: list[tuple[str, int]] = []

        self._build()

    def resize(self, screen_size: tuple[int, int]) -> None:
        screen_width, screen_height = screen_size
        old_x = self.rect.x
        self.rect.x = screen_width - PANEL_WIDTH
        self.rect.height = screen_height

        # Shift every button by the same delta rather than rebuilding from
        # scratch — a full _build() would reset whichever density/stream/
        # tool button is currently pressed back to the hardcoded defaults,
        # discarding the user's actual selection. Confirmed this was a real,
        # visible bug before this fix: after widening the window, buttons
        # stayed frozen at their old x position while the panel background
        # (drawn from self.rect directly) moved to track the new width.
        dx = self.rect.x - old_x
        if dx:
            for group in (self.terrain_group, self.stream_group, self.tool_group, self.zone_player_group):
                for btn in group.buttons:
                    btn.rect.x += dx
            for btn in self._action_buttons:
                btn.rect.x += dx
            self._azn_value_center = (self._azn_value_center[0] + dx, self._azn_value_center[1])

    def _build(self) -> None:
        self._headers = []
        x = self.rect.x + PADDING
        y = 10

        y += 24  # title

        # Terrain
        self._headers.append(("Terrain", y))
        y += 18
        size = 48
        densities = [Density.LOW, Density.MEDIUM, Density.HIGH, Density.BONE]
        labels = {Density.LOW: "LOW", Density.MEDIUM: "MED", Density.HIGH: "HIGH", Density.BONE: "BONE"}
        tooltips = {
            Density.LOW: "Low density — 2 turns/step",
            Density.MEDIUM: "Medium density — 3 turns/step",
            Density.HIGH: "High density — 4 turns/step",
            Density.BONE: "Bone — impassable",
        }
        for i, d in enumerate(densities):
            bx = x + (i % 4) * (size + 2)
            by = y + (i // 4) * (size + 2)
            btn = Button((bx, by, size, size), labels[d],
                         on_click=lambda d=d: self._select_density(d), pressed=(d == Density.LOW),
                         tooltip=tooltips[d])
            self.terrain_group.add(btn)
        y += size + 10

        # Streams
        self._headers.append(("Stream Direction", y))
        y += 18
        dirs = [StreamDir.NORTH, StreamDir.SOUTH, StreamDir.EAST, StreamDir.WEST]
        dir_labels = {StreamDir.NORTH: "^", StreamDir.SOUTH: "v", StreamDir.EAST: ">", StreamDir.WEST: "<"}
        dir_names = {StreamDir.NORTH: "North", StreamDir.SOUTH: "South", StreamDir.EAST: "East", StreamDir.WEST: "West"}
        for i, sd in enumerate(dirs):
            bx = x + i * (size + 2)
            btn = Button((bx, y, size, size), dir_labels[sd],
                         on_click=lambda sd=sd: self._select_stream(sd), pressed=(sd == StreamDir.NORTH),
                         tooltip=f"Stream direction: {dir_names[sd]}")
            self.stream_group.add(btn)
        y += size + 10

        # Elements — icon buttons (tooltips carry the name) instead of
        # full-width text rows, so the row of tools reads at a glance
        # instead of as a stack of labels you have to read one by one.
        self._headers.append(("Elements", y))
        y += 18
        for i, (icon_fn, tool_name, name) in enumerate([
            (icons.habitas_icon, "habitas", "Place Habitas"),
            (icons.azn_icon, "azn", "Place AZN"),
            (icons.zone_icon, "zone", "Place Zone"),
            (icons.white_cell_icon, "hazard", "White Cell patrol (click waypoints, right-click to finish)"),
        ]):
            bx = x + i * (size + 2)
            btn = Button((bx, y, size, size), "", on_click=lambda t=tool_name: self._select_tool(t),
                         tooltip=name, icon=icon_fn(28))
            self.tool_group.add(btn)
            self._tool_buttons_by_name[tool_name] = btn
        y += size + 10

        # Zone owner — which player a newly-placed injection zone belongs
        # to (MAP-08: the editor previously always placed player-1 zones,
        # so a full 2-player map couldn't be authored without hand-editing
        # the JSON).
        self._headers.append(("Zone Owner", y))
        y += 18
        for i, label in enumerate(["P1", "P2"]):
            btn = Button((x + i * 50, y, 46, 26), label, pressed=(i == 0),
                         on_click=lambda idx=i: self._select_zone_player(idx),
                         tooltip=f"New zones belong to Player {i + 1}")
            self.zone_player_group.add(btn)
        y += 26 + 10

        # Tools
        self._headers.append(("Tools", y))
        y += 18
        for i, (icon_fn, tool_name, name) in enumerate([
            (icons.pan_icon, "pan", "Pan"),
            (icons.edit_icon, "edit", "Edit"),
            (icons.delete_icon, "delete", "Delete"),
        ]):
            bx = x + i * (size + 2)
            btn = Button((bx, y, size, size), "", on_click=lambda t=tool_name: self._select_tool(t),
                         tooltip=name, icon=icon_fn(28))
            self.tool_group.add(btn)
            self._tool_buttons_by_name[tool_name] = btn
        y += size + 10

        # Map settings: the starting AZN budget both players get. Was
        # write-only from the editor's perspective (round-tripped since
        # v0.0.2 but with no UI to change it).
        self._headers.append(("Starting AZN", y))
        y += 18
        half = (PANEL_WIDTH - 2 * PADDING - 8) // 2
        self.azn_minus_btn = Button((x, y, 34, 26), "-25",
                                    on_click=lambda: self._fire_azn_delta(-25),
                                    tooltip="Both players start each match with this AZN budget")
        self.azn_plus_btn = Button((x + PANEL_WIDTH - 2 * PADDING - 34, y, 34, 26), "+25",
                                   on_click=lambda: self._fire_azn_delta(25))
        self._azn_value_center = (x + (PANEL_WIDTH - 2 * PADDING) // 2, y + 13)
        self._action_buttons.extend([self.azn_minus_btn, self.azn_plus_btn])
        y += 26 + 10

        # File row 1: New + Load share a row (the sidebar is near its
        # height budget at the 1024x640 minimum window size).
        btn_new = Button((x, y, half, ROW_HEIGHT), "New",
                         on_click=lambda: self._fire("on_new"),
                         tooltip="Blank map with a size you choose (warns about unsaved changes)")
        btn_load = Button((x + half + 8, y, half, ROW_HEIGHT), "Load",
                          on_click=lambda: self._fire("on_load"),
                          tooltip="Open a map from maps/ (warns about unsaved changes)")
        self._action_buttons.extend([btn_new, btn_load])
        y += ROW_HEIGHT + 4
        for label, attr, tip in [("Save", "on_save", "Save to maps/ (Ctrl+S)"),
                                  ("Clear Map", "on_clear", "Wipe the whole map (undoable)")]:
            btn = Button((x, y, PANEL_WIDTH - 2 * PADDING, ROW_HEIGHT), label,
                         on_click=lambda a=attr: self._fire(a), tooltip=tip)
            self._action_buttons.append(btn)
            y += ROW_HEIGHT + 4
        y += 6

        # History
        self._headers.append(("History", y))
        y += 18
        self.undo_btn = Button((x, y, half, ROW_HEIGHT), "Undo",
                                on_click=lambda: self._fire("on_undo"), tooltip="Ctrl+Z")
        self.undo_btn.enabled = False
        self.redo_btn = Button((x + half + 8, y, half, ROW_HEIGHT), "Redo",
                                on_click=lambda: self._fire("on_redo"), tooltip="Ctrl+Y / Ctrl+Shift+Z")
        self.redo_btn.enabled = False
        self._action_buttons.extend([self.undo_btn, self.redo_btn])

    def _select_density(self, d: Density) -> None:
        if self.on_density:
            self.on_density(d)

    def _select_stream(self, sd: StreamDir) -> None:
        if self.on_stream_dir:
            self.on_stream_dir(sd)

    def _select_tool(self, name: str) -> None:
        if self.on_tool:
            self.on_tool(name)

    def _select_zone_player(self, idx: int) -> None:
        if self.on_zone_player:
            self.on_zone_player(idx)

    def set_active_tool(self, name: str) -> None:
        """Highlight whichever of Habitas/AZN/Zone/Pan/Edit/Delete is active,
        or none of them if the active tool is Terrain/Stream (those show
        their current value via terrain_group/stream_group instead)."""
        for tool_name, btn in self._tool_buttons_by_name.items():
            btn.pressed = (tool_name == name)

    def _fire(self, attr: str) -> None:
        cb = getattr(self, attr, None)
        if cb:
            cb()

    def _fire_azn_delta(self, delta: int) -> None:
        if self.on_azn_delta:
            self.on_azn_delta(delta)

    def set_starting_azn(self, value: int) -> None:
        self._starting_azn_display = value

    def set_undo_enabled(self, enabled: bool) -> None:
        if self.undo_btn:
            self.undo_btn.enabled = enabled

    def set_redo_enabled(self, enabled: bool) -> None:
        if self.redo_btn:
            self.redo_btn.enabled = enabled

    def handle_event(self, event: "pygame.event.Event") -> bool:
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            pos = event.pos
            if not self.rect.collidepoint(pos) and event.type == pygame.MOUSEBUTTONDOWN:
                return False

        handled = False
        if self.terrain_group.handle_event(event):
            handled = True
        if self.stream_group.handle_event(event):
            handled = True
        if self.tool_group.handle_event(event):
            handled = True
        if self.zone_player_group.handle_event(event):
            handled = True
        for btn in self._action_buttons:
            if btn.handle_event(event):
                handled = True
        return handled

    def draw(self, surface: "pygame.Surface") -> None:
        pygame.draw.rect(surface, (38, 38, 38), self.rect)
        pygame.draw.line(surface, (20, 20, 20), (self.rect.left, 0), (self.rect.left, self.rect.height), 2)

        tx = self.rect.x + PADDING
        draw_text(surface, "Map Editor", (tx, 8), size=16, color=(235, 235, 235))
        for label, header_y in self._headers:
            draw_text(surface, label, (tx, header_y), size=11, color=(160, 165, 180))

        self.terrain_group.draw(surface)
        self.stream_group.draw(surface)
        self.tool_group.draw(surface)
        self.zone_player_group.draw(surface)
        for btn in self._action_buttons:
            btn.draw(surface)

        value = get_font(14).render(str(self._starting_azn_display), True, (230, 210, 120))
        surface.blit(value, value.get_rect(center=self._azn_value_center))

        # Tooltips drawn last so they overlay everything else — via the
        # shared widgets helper (this sidebar used to be the only place in
        # the app that rendered tooltips at all).
        tooltip_buttons = [btn for group in (self.terrain_group, self.stream_group,
                                              self.tool_group, self.zone_player_group)
                           for btn in group.buttons]
        draw_hover_tooltips(surface, tooltip_buttons + self._action_buttons)
