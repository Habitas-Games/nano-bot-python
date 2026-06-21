"""Every tool in the editor follows the same convention: call
history.save_state(doc) immediately *before* mutating doc, for every
single discrete edit (including the very first one after load — see
MapEditorScreen._load_map_from_file, which calls save_state() once right
after loading to establish the baseline, then every tool's handle_press
calls it again before its own first mutation). The `edit()` helper below
mirrors that exact convention so these tests reflect real usage instead
of a guessed-at calling pattern."""

from nanobot.core.map_data import Density
from nanobot.ui.map_editor import map_document_ops as ops
from nanobot.ui.map_editor import map_history as map_history_module
from nanobot.ui.map_editor.map_history import MapHistory


def edit(history, m, mutate_fn):
    """One discrete editor action: save_state() then mutate — the same
    order every tool actually uses."""
    history.save_state(m)
    mutate_fn(m)


class TestMapHistory:
    def test_cannot_undo_with_no_history(self):
        h = MapHistory()
        assert h.can_undo() is False

    def test_single_save_state_is_not_enough_to_undo(self):
        # The first save_state() establishes the baseline — undoing past it
        # would have nothing to restore to, so can_undo() must require at
        # least 2 entries.
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)
        assert h.can_undo() is False

    def test_undo_restores_previous_state(self):
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)  # baseline, established at load time
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.HIGH))

        h.undo(m)
        assert m.get_cell(1, 1)["density"] == Density.LOW  # back to baseline

    def test_one_undo_reverts_only_the_most_recent_of_two_edits(self):
        # This is the exact scenario that exposed a real off-by-one bug:
        # undo() used to decrement its pointer *before* restoring, which
        # skipped the entry representing "one edit ago" and jumped back
        # two edits instead of one.
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)  # baseline
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.HIGH))
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.BONE))

        h.undo(m)
        assert m.get_cell(1, 1)["density"] == Density.HIGH  # only the BONE edit undone

    def test_undo_twice_reaches_the_original_baseline(self):
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.HIGH))
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.BONE))

        h.undo(m)
        h.undo(m)
        assert m.get_cell(1, 1)["density"] == Density.LOW

    def test_undo_past_the_baseline_is_a_noop(self):
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.HIGH))

        h.undo(m)
        assert h.can_undo() is False
        h.undo(m)  # must not raise or corrupt state
        assert m.get_cell(1, 1)["density"] == Density.LOW

    def test_undo_restores_habitas_points(self):
        # The bug this whole class exists to avoid repeating: the Godot
        # port's undo only ever snapshotted `cells`, so placing/moving/
        # deleting a habitas point was never actually undoable.
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)
        edit(h, m, lambda m: ops.place_habitas(m, 2, 2))
        edit(h, m, lambda m: ops.place_habitas(m, 3, 3))

        h.undo(m)
        assert m.habitas_points == [(2, 2)]

        h.undo(m)
        assert m.habitas_points == []

    def test_redo_branch_is_discarded_after_a_new_action(self):
        h = MapHistory()
        m = ops.init_blank(5, 5)
        h.save_state(m)
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.HIGH))
        edit(h, m, lambda m: ops.paint_cell(m, 1, 1, Density.BONE))

        h.undo(m)  # back to HIGH; the BONE state is now a "redo" branch
        edit(h, m, lambda m: ops.paint_cell(m, 2, 2, Density.MEDIUM))  # discards that branch

        h.undo(m)
        assert m.get_cell(2, 2)["density"] == Density.LOW  # back before the MEDIUM paint
        assert m.get_cell(1, 1)["density"] == Density.HIGH  # the BONE state never comes back

        h.undo(m)
        assert m.get_cell(1, 1)["density"] == Density.LOW  # back to baseline
        assert h.can_undo() is False  # the discarded BONE state is unreachable

    def test_history_is_capped_at_max_history(self):
        h = MapHistory()
        m = ops.init_blank(3, 3)
        h.save_state(m)
        for i in range(map_history_module.MAX_HISTORY + 20):
            edit(h, m, lambda m, i=i: ops.paint_cell(m, 0, 0, Density.LOW if i % 2 == 0 else Density.HIGH))
        assert len(h._history) <= map_history_module.MAX_HISTORY
