from __future__ import annotations

from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool

DEFAULT_QUANTITY = 30


class AznTool(EditorTool):
    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if button != 1 or not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        if ops.find_element_at(self.editor.doc, *grid_pos)["type"] != "none":
            return True
        self.editor.history.save_state(self.editor.doc)
        ops.place_azn(self.editor.doc, *grid_pos, DEFAULT_QUANTITY)
        return True

    def get_status_text(self) -> str:
        return "Tool: Place AZN | Click to place"
