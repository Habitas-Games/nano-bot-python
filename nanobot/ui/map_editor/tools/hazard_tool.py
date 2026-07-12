"""White-cell (hazard) authoring tool — closes MAP-08's last gap.

Click passable cells to lay down patrol waypoints; the path is drawn
live as you go. Right-click (or Enter) commits the patrol — a single
waypoint makes a stationary guard, more make a loop. Backspace removes
the last pending waypoint. With no patrol in progress, right-clicking
any existing patrol's waypoint deletes that patrol. Keys 1/2/3 set the
next patrol's speed (steps every 1/2/3 turns).

Combat stats use the shipped maps' proven defaults (hp 45, damage 3,
contact range 1.5); fine-tuning beyond speed stays in the map JSON —
the editor's job is authoring where patrols roam, which was the part
that was impossible without hand-writing coordinates."""

from __future__ import annotations

import pygame

from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor.tools.editor_tool import EditorTool

DEFAULT_HP = 45
DEFAULT_DAMAGE = 3
DEFAULT_RANGE = 1.5


class HazardTool(EditorTool):
    def __init__(self, editor):
        super().__init__(editor)
        self.pending: list[tuple[int, int]] = []
        self.move_every = 2
        self._notice = ""

    def on_deactivate(self) -> None:
        self.pending = []
        self._notice = ""

    def _commit(self) -> None:
        if not self.pending:
            return
        self.editor.history.save_state(self.editor.doc)
        ops.add_hazard(self.editor.doc, self.pending, hp=DEFAULT_HP, damage=DEFAULT_DAMAGE,
                       range_=DEFAULT_RANGE, move_every=self.move_every)
        self.pending = []
        self._notice = "Patrol placed"

    def handle_press(self, grid_pos: tuple[int, int], button: int) -> bool:
        if not self.editor.doc.is_in_bounds(*grid_pos):
            return False
        if button == 1:
            if not self.editor.doc.is_passable(*grid_pos):
                self._notice = "Waypoint must be on passable terrain"
                return True
            self.pending.append(grid_pos)
            self._notice = ""
            return True
        if button == 3:
            if self.pending:
                self._commit()
                return True
            idx = ops.find_hazard_at(self.editor.doc, *grid_pos)
            if idx >= 0:
                self.editor.history.save_state(self.editor.doc)
                ops.delete_hazard(self.editor.doc, idx)
                self._notice = "Patrol deleted"
                return True
        return False

    def handle_key(self, event: "pygame.event.Event") -> bool:
        if event.key == pygame.K_RETURN and self.pending:
            self._commit()
            return True
        if event.key == pygame.K_BACKSPACE and self.pending:
            self.pending.pop()
            return True
        if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.move_every = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[event.key]
            return True
        return False

    def get_status_text(self) -> str:
        speed = f"speed: every {self.move_every} turn{'s' if self.move_every > 1 else ''} (keys 1/2/3)"
        suffix = f" | {self._notice}" if self._notice else ""
        if self.pending:
            return (f"White cell path: {len(self.pending)} waypoint(s) | Click: add | "
                    f"Right-click/Enter: finish | Backspace: undo point | {speed}{suffix}")
        return (f"Tool: White Cell | Click: start patrol path | "
                f"Right-click a patrol: delete | {speed}{suffix}")

    def get_cursor(self) -> int:
        return pygame.SYSTEM_CURSOR_CROSSHAIR
