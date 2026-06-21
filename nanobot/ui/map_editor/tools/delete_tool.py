from __future__ import annotations

from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class DeleteTool(EditorTool):
    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if button != 1 or not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        self.editor.history.save_state(self.editor.doc)
        ops.delete_at_position(self.editor.doc, *grid_pos)
        self.editor.last_paint_pos = grid_pos
        self.editor.brush_cursor_pos = grid_pos
        return True

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        if not self.editor.doc.is_in_bounds(*grid_pos):
            return
        self.editor.brush_cursor_pos = grid_pos
        if grid_pos != self.editor.last_paint_pos:
            ops.delete_at_position(self.editor.doc, *grid_pos)
            self.editor.last_paint_pos = grid_pos

    def handle_release(self) -> None:
        self.editor.brush_cursor_pos = (-1, -1)

    def get_status_text(self) -> str:
        return "Tool: Delete | Click + drag to erase terrain, streams, elements"
