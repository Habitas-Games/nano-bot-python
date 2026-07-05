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

    @property
    def position(self) -> int:
        """Current index in the undo stack — the editor compares this
        against the position it recorded at the last save/load to know
        whether the document has unsaved changes (undoing back to the
        saved position correctly counts as clean again)."""
        return self._index

    def undo(self, m: MapData) -> None:
        """Restore the state as of right before the most recently completed
        edit, then step the pointer back for the next undo call.

        save_state() is always called *before* a mutation (every tool does
        `history.save_state(doc); ops.mutate(doc)`), so `_history[_index]`
        already holds exactly "the state right before the last edit" — the
        correct target for one Undo. Decrementing _index before restoring
        (as an earlier version of this method did, faithfully inherited
        from a bug in the original Godot implementation) reads the *wrong*
        entry: after two separate edits, a single Undo would revert both
        at once instead of just the most recent one, since it skips past
        the entry that actually represents "one edit ago."
        """
        if not self.can_undo():
            return
        ops.restore(m, self._history[self._index])
        self._index -= 1
