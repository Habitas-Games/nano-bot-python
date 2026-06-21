"""Base class for map editor tools — same architecture as the Godot
project's v0.0.3 refactor (docs/versioning/v0.0.3 in nano-bot): one class
per tool owning its own press/drag/release/key/cursor/status behavior,
instead of one giant per-event switch statement keyed by a tool-name
string. `editor` is the MapEditorScreen; tools call back into its small
public surface (doc, history, selected_density, etc.)."""

from __future__ import annotations

import pygame


class EditorTool:
    def __init__(self, editor):
        self.editor = editor

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        """Return True if handled (caller starts a drag)."""
        return False

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        pass

    def handle_release(self) -> None:
        pass

    def handle_key(self, event: "pygame.event.Event") -> bool:
        """Return True if handled."""
        return False

    def get_status_text(self) -> str:
        return ""

    def get_cursor(self) -> int:
        return pygame.SYSTEM_CURSOR_ARROW
