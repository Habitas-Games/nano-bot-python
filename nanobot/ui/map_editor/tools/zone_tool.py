"""Drag rectangle to place an injection zone, owned by whichever player
is selected in the sidebar's Zone Owner toggle (MAP-08)."""

from __future__ import annotations

from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool


class ZoneTool(EditorTool):
    def __init__(self, editor):
        super().__init__(editor)
        self._drag_start: tuple[int, int] | None = None
        self._drag_current: tuple[int, int] | None = None

    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if button != 1 or not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        self._drag_start = grid_pos
        self._drag_current = grid_pos
        self.editor.preview_rect = (grid_pos[0], grid_pos[1], 1, 1)
        return True

    def handle_drag(self, grid_pos: tuple[int, int], rel: tuple[int, int]) -> None:
        if self._drag_start is None or not self.editor.doc.is_in_bounds(*grid_pos):
            return
        self._drag_current = grid_pos
        self.editor.preview_rect = self._compute_rect()

    def handle_release(self) -> None:
        if self._drag_start is not None:
            rect = self._compute_rect()
            self.editor.history.save_state(self.editor.doc)
            ops.place_zone(self.editor.doc, rect, player=self.editor.zone_player)
        self._drag_start = None
        self._drag_current = None
        self.editor.preview_rect = None

    def _compute_rect(self) -> tuple[int, int, int, int]:
        x1 = min(self._drag_start[0], self._drag_current[0])
        y1 = min(self._drag_start[1], self._drag_current[1])
        x2 = max(self._drag_start[0], self._drag_current[0])
        y2 = max(self._drag_start[1], self._drag_current[1])
        return (x1, y1, x2 - x1 + 1, y2 - y1 + 1)

    def get_status_text(self) -> str:
        return f"Tool: Place Zone | Drag to create rectangle (Player {self.editor.zone_player + 1}; use Edit tool to reposition)"
