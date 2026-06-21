"""Right-hand control panel for the map editor. Builds Button widgets and
exposes user intent through plain callback attributes (on_density,
on_stream_dir, on_tool, on_load, on_save, on_clear, on_undo) — the pygame
equivalent of the Godot sidebar's Signals."""

from __future__ import annotations

import pygame

from nanobot.core.map_data import Density, StreamDir
from nanobot.ui.widgets import Button, ButtonGroup, draw_text

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
        self.on_load = None
        self.on_save = None
        self.on_clear = None
        self.on_undo = None

        self.terrain_group = ButtonGroup()
        self.stream_group = ButtonGroup()
        self.undo_btn: Button | None = None
        self._action_buttons: list[Button] = []

        self._build()

    def resize(self, screen_size: tuple[int, int]) -> None:
        screen_width, screen_height = screen_size
        self.rect.x = screen_width - PANEL_WIDTH
        self.rect.height = screen_height

    def _build(self) -> None:
        x = self.rect.x + PADDING
        y = 10

        y += 24  # title

        # Terrain
        y += 18
        size = 48
        densities = [Density.LOW, Density.MEDIUM, Density.HIGH, Density.BONE]
        labels = {Density.LOW: "LOW\n2t", Density.MEDIUM: "MED\n3t", Density.HIGH: "HIGH\n4t", Density.BONE: "BONE\nX"}
        for i, d in enumerate(densities):
            bx = x + (i % 4) * (size + 2)
            by = y + (i // 4) * (size + 2)
            btn = Button((bx, by, size, size), labels[d].split("\n")[0],
                         on_click=lambda d=d: self._select_density(d), pressed=(d == Density.LOW))
            self.terrain_group.add(btn)
        y += size + 10

        # Streams
        y += 18
        dirs = [StreamDir.NORTH, StreamDir.SOUTH, StreamDir.EAST, StreamDir.WEST]
        dir_labels = {StreamDir.NORTH: "^", StreamDir.SOUTH: "v", StreamDir.EAST: ">", StreamDir.WEST: "<"}
        for i, sd in enumerate(dirs):
            bx = x + i * (size + 2)
            btn = Button((bx, y, size, size), dir_labels[sd],
                         on_click=lambda sd=sd: self._select_stream(sd), pressed=(sd == StreamDir.NORTH))
            self.stream_group.add(btn)
        y += size + 10

        # Elements
        y += 18
        for label, tool_name in [("Place Habitas", "habitas"), ("Place AZN", "azn"), ("Place Zone", "zone")]:
            btn = Button((x, y, PANEL_WIDTH - 2 * PADDING, ROW_HEIGHT), label,
                         on_click=lambda t=tool_name: self._select_tool(t))
            self._action_buttons.append(btn)
            y += ROW_HEIGHT + 4
        y += 6

        # Tools
        y += 18
        for label, tool_name in [("Pan", "pan"), ("Edit", "edit"), ("Delete", "delete")]:
            btn = Button((x, y, PANEL_WIDTH - 2 * PADDING, ROW_HEIGHT), label,
                         on_click=lambda t=tool_name: self._select_tool(t))
            self._action_buttons.append(btn)
            y += ROW_HEIGHT + 4
        for label, attr in [("Load", "on_load"), ("Save", "on_save"), ("Clear Map", "on_clear")]:
            btn = Button((x, y, PANEL_WIDTH - 2 * PADDING, ROW_HEIGHT), label,
                         on_click=lambda a=attr: self._fire(a))
            self._action_buttons.append(btn)
            y += ROW_HEIGHT + 4
        y += 6

        # History
        y += 18
        self.undo_btn = Button((x, y, PANEL_WIDTH - 2 * PADDING, ROW_HEIGHT), "Undo",
                                on_click=lambda: self._fire("on_undo"))
        self.undo_btn.enabled = False
        self._action_buttons.append(self.undo_btn)

    def _select_density(self, d: Density) -> None:
        if self.on_density:
            self.on_density(d)

    def _select_stream(self, sd: StreamDir) -> None:
        if self.on_stream_dir:
            self.on_stream_dir(sd)

    def _select_tool(self, name: str) -> None:
        if self.on_tool:
            self.on_tool(name)

    def _fire(self, attr: str) -> None:
        cb = getattr(self, attr, None)
        if cb:
            cb()

    def set_undo_enabled(self, enabled: bool) -> None:
        if self.undo_btn:
            self.undo_btn.enabled = enabled

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
        for btn in self._action_buttons:
            if btn.handle_event(event):
                handled = True
        return handled

    def draw(self, surface: "pygame.Surface") -> None:
        pygame.draw.rect(surface, (38, 38, 38), self.rect)
        pygame.draw.line(surface, (20, 20, 20), (self.rect.left, 0), (self.rect.left, self.rect.height), 2)

        tx = self.rect.x + PADDING
        draw_text(surface, "Map Editor", (tx, 8), size=16, color=(235, 235, 235))
        draw_text(surface, "Terrain", (tx, 36), size=11, color=(160, 165, 180))
        self.terrain_group.draw(surface)
        draw_text(surface, "Stream Direction", (tx, 36 + 18 + 50 + 10), size=11, color=(160, 165, 180))
        self.stream_group.draw(surface)

        y_elements_header = 36 + 18 + 50 + 10 + 18 + 50 + 10
        draw_text(surface, "Elements", (tx, y_elements_header), size=11, color=(160, 165, 180))

        y_tools_header = y_elements_header + 18 + 3 * (ROW_HEIGHT + 4) + 6
        draw_text(surface, "Tools", (tx, y_tools_header), size=11, color=(160, 165, 180))

        y_history_header = y_tools_header + 18 + 6 * (ROW_HEIGHT + 4) + 6
        draw_text(surface, "History", (tx, y_history_header), size=11, color=(160, 165, 180))

        for btn in self._action_buttons:
            btn.draw(surface)
