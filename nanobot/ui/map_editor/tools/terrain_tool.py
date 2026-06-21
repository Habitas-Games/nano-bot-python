from __future__ import annotations

import pygame

from nanobot.core import map_loader
from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class TerrainTool(EditorTool):
    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if not self.editor.doc.is_in_bounds(*grid_pos):
            return False

        if button == 1:  # left
            self.editor.history.save_state(self.editor.doc)
            ops.paint_cell(self.editor.doc, *grid_pos, self.editor.selected_density)
            self.editor.last_paint_pos = grid_pos
            self.editor.brush_cursor_pos = grid_pos
            return True
        elif button == 3:  # right
            self.editor.history.save_state(self.editor.doc)
            ops.flood_fill(self.editor.doc, *grid_pos, self.editor.selected_density)
            return True
        return False

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        if not self.editor.doc.is_in_bounds(*grid_pos):
            return
        self.editor.brush_cursor_pos = grid_pos
        if grid_pos != self.editor.last_paint_pos:
            ops.paint_cell(self.editor.doc, *grid_pos, self.editor.selected_density)
            self.editor.last_paint_pos = grid_pos

    def handle_release(self) -> None:
        self.editor.brush_cursor_pos = (-1, -1)

    def get_status_text(self) -> str:
        density_name = map_loader.density_to_string(self.editor.selected_density).upper()
        return f"Tool: Terrain ({density_name}) | Click: paint | Right-click: fill | Scroll: zoom"
