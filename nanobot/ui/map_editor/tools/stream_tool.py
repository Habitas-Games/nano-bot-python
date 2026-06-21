from __future__ import annotations

from nanobot.core import map_loader
from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class StreamTool(EditorTool):
    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if button != 1 or not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        self.editor.history.save_state(self.editor.doc)
        ops.place_stream(self.editor.doc, *grid_pos, self.editor.selected_stream_dir)
        self.editor.last_paint_pos = grid_pos
        return True

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        if not self.editor.doc.is_in_bounds(*grid_pos):
            return
        if grid_pos != self.editor.last_paint_pos:
            ops.place_stream(self.editor.doc, *grid_pos, self.editor.selected_stream_dir)
            self.editor.last_paint_pos = grid_pos

    def get_status_text(self) -> str:
        dir_name = map_loader.stream_to_string(self.editor.selected_stream_dir).upper()
        return f"Tool: Stream ({dir_name}) | Click to place stream"
