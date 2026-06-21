"""Undo stack for the map editor. Snapshots the *entire* MapData (cells +
every element list) on every save_state() call — the Godot version of
this editor originally snapshotted cells only, even though save_state()
was called before element mutations too, so Undo silently never restored
a placed/moved/deleted habitas point, AZN node, or zone in any commit
since that project's Phase 2. Fixed at the source here from the start."""

from __future__ import annotations

from nanobot.core.map_data import MapData
from nanobot.ui.map_editor import map_document_ops as ops

MAX_HISTORY = 50


class MapHistory:
    def __init__(self):
        self._history: list[dict] = []
        self._index = -1

    def reset(self) -> None:
        self._history.clear()
        self._index = -1

    def save_state(self, m: MapData) -> None:
        if self._index < len(self._history) - 1:
            del self._history[self._index + 1:]

        self._history.append(ops.snapshot(m))
        self._index = len(self._history) - 1

        if len(self._history) > MAX_HISTORY:
            self._history.pop(0)
            self._index -= 1

    def can_undo(self) -> bool:
        return self._index > 0

    def undo(self, m: MapData) -> None:
        if not self.can_undo():
            return
        self._index -= 1
        ops.restore(m, self._history[self._index])
