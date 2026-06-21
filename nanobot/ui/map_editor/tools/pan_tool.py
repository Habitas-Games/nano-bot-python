from __future__ import annotations

import pygame

from nanobot.ui.map_editor.map_canvas_renderer import CELL_SIZE
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class PanTool(EditorTool):
    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        return button == 1

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        e = self.editor
        max_x = max(0, int(e.doc.width * CELL_SIZE * e.zoom - e.canvas_rect.width))
        max_y = max(0, int(e.doc.height * CELL_SIZE * e.zoom - e.canvas_rect.height))
        e.scroll_x = max(0, min(e.scroll_x - rel[0], max_x))
        e.scroll_y = max(0, min(e.scroll_y - rel[1], max_y))

    def get_status_text(self) -> str:
        return "Tool: Pan ✋ | Click + drag to move map"

    def get_cursor(self) -> int:
        return pygame.SYSTEM_CURSOR_SIZEALL
