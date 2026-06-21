"""map_document_ops carries the editor-specific fixes from the Godot
port's v0.0.3 cleanup: a duplicate-position guard on element placement,
and snapshot()/restore() covering every element list (not just cells —
the Godot version's undo silently never restored habitas/AZN/zones for
its entire lifetime until that cleanup). Both are tested explicitly here
since they're the whole reason this module looks the way it does."""

import pytest

from nanobot.core.map_data import Density, MapData, StreamDir
from nanobot.ui.map_editor import map_document_ops as ops


def blank(width=10, height=10):
    return ops.init_blank(width, height)


class TestInitBlank:
    def test_dimensions(self):
        m = blank(7, 9)
        assert (m.width, m.height) == (7, 9)
        assert len(m._cells) == 63

    def test_default_density_applies_to_all_cells(self):
        m = ops.init_blank(5, 5, default_density=Density.HIGH)
        assert all(c["density"] == Density.HIGH for c in m._cells)

    def test_no_streams_by_default(self):
        m = blank()
        assert all(c["stream_dir"] == StreamDir.NONE for c in m._cells)


class TestPaintAndFill:
    def test_paint_cell_changes_density(self):
        m = blank()
        ops.paint_cell(m, 3, 3, Density.BONE)
        assert m.get_cell(3, 3)["density"] == Density.BONE

    def test_paint_cell_out_of_bounds_is_a_noop(self):
        m = blank()
        ops.paint_cell(m, -1, -1, Density.BONE)  # must not raise

    def test_place_stream_sets_direction(self):
        m = blank()
        ops.place_stream(m, 2, 2, StreamDir.EAST)
        assert m.get_cell(2, 2)["stream_dir"] == StreamDir.EAST

    def test_flood_fill_changes_connected_region_only(self):
        m = blank(5, 5)  # all LOW
        ops.paint_cell(m, 0, 0, Density.BONE)  # isolate top-left corner... actually need a region
        # Build an island of MEDIUM in the top-left 2x2, separated from the rest by BONE.
        for x, y in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            ops.paint_cell(m, x, y, Density.MEDIUM)
        ops.flood_fill(m, 0, 0, Density.HIGH)
        assert m.get_cell(0, 0)["density"] == Density.HIGH
        assert m.get_cell(1, 1)["density"] == Density.HIGH
        # Cells that were never MEDIUM must be untouched.
        assert m.get_cell(4, 4)["density"] == Density.LOW

    def test_flood_fill_does_not_cross_different_density(self):
        m = blank(5, 5)
        ops.paint_cell(m, 2, 2, Density.HIGH)
        ops.flood_fill(m, 0, 0, Density.BONE)  # fills the LOW region
        assert m.get_cell(2, 2)["density"] == Density.HIGH  # the HIGH island is untouched

    def test_flood_fill_same_target_and_new_density_is_a_noop(self):
        m = blank(5, 5)
        ops.flood_fill(m, 0, 0, Density.LOW)  # already LOW everywhere
        assert all(c["density"] == Density.LOW for c in m._cells)


class TestClearAll:
    def test_clear_resets_terrain_and_streams(self):
        m = blank()
        ops.paint_cell(m, 1, 1, Density.BONE)
        ops.place_stream(m, 2, 2, StreamDir.NORTH)
        ops.clear_all(m)
        assert all(c["density"] == Density.LOW for c in m._cells)
        assert all(c["stream_dir"] == StreamDir.NONE for c in m._cells)

    def test_clear_removes_all_elements(self):
        m = blank()
        ops.place_habitas(m, 1, 1)
        ops.place_azn(m, 2, 2)
        ops.place_zone(m, (0, 0, 2, 2))
        ops.clear_all(m)
        assert m.habitas_points == []
        assert m.azn_nodes == []
        assert m.injection_zones == []


class TestDeleteAtPosition:
    def test_delete_resets_terrain_to_low_and_clears_stream(self):
        m = blank()
        ops.paint_cell(m, 3, 3, Density.HIGH)
        ops.place_stream(m, 3, 3, StreamDir.SOUTH)
        ops.delete_at_position(m, 3, 3)
        assert m.get_cell(3, 3)["density"] == Density.LOW
        assert m.get_cell(3, 3)["stream_dir"] == StreamDir.NONE

    def test_delete_removes_habitas_at_position(self):
        m = blank()
        ops.place_habitas(m, 3, 3)
        ops.delete_at_position(m, 3, 3)
        assert m.habitas_points == []

    def test_delete_removes_azn_at_position(self):
        m = blank()
        ops.place_azn(m, 3, 3)
        ops.delete_at_position(m, 3, 3)
        assert m.azn_nodes == []

    def test_delete_removes_zone_containing_position(self):
        m = blank()
        ops.place_zone(m, (0, 0, 5, 5))
        ops.delete_at_position(m, 2, 2)  # inside the zone
        assert m.injection_zones == []

    def test_delete_does_not_affect_other_elements(self):
        m = blank()
        ops.place_habitas(m, 1, 1)
        ops.place_habitas(m, 8, 8)
        ops.delete_at_position(m, 1, 1)
        assert m.habitas_points == [(8, 8)]


class TestPlacementDuplicateGuard:
    def test_place_habitas_succeeds_on_empty_cell(self):
        m = blank()
        assert ops.place_habitas(m, 2, 2) is True
        assert (2, 2) in m.habitas_points

    def test_place_habitas_twice_on_same_cell_is_rejected(self):
        m = blank()
        ops.place_habitas(m, 2, 2)
        assert ops.place_habitas(m, 2, 2) is False
        assert m.habitas_points == [(2, 2)]  # still just one entry

    def test_place_azn_twice_on_same_cell_is_rejected(self):
        m = blank()
        ops.place_azn(m, 2, 2, quantity=10)
        assert ops.place_azn(m, 2, 2, quantity=99) is False
        assert m.azn_nodes == [{"position": (2, 2), "quantity": 10}]  # second call had no effect

    def test_place_out_of_bounds_is_rejected(self):
        m = blank()
        assert ops.place_habitas(m, -1, -1) is False
        assert ops.place_azn(m, 999, 999) is False


class TestFindElementAt:
    def test_finds_habitas(self):
        m = blank()
        ops.place_habitas(m, 3, 3)
        assert ops.find_element_at(m, 3, 3) == {"type": "habitas", "index": 0}

    def test_finds_azn(self):
        m = blank()
        ops.place_azn(m, 4, 4)
        assert ops.find_element_at(m, 4, 4) == {"type": "azn", "index": 0}

    def test_finds_zone_by_containment_not_just_corner(self):
        m = blank()
        ops.place_zone(m, (0, 0, 5, 5))
        assert ops.find_element_at(m, 3, 3) == {"type": "zone", "index": 0}

    def test_empty_cell_returns_none_type(self):
        m = blank()
        assert ops.find_element_at(m, 5, 5) == {"type": "none"}

    def test_habitas_takes_priority_over_zone_at_same_cell(self):
        m = blank()
        ops.place_zone(m, (0, 0, 5, 5))
        ops.place_habitas(m, 2, 2)
        assert ops.find_element_at(m, 2, 2)["type"] == "habitas"


class TestMoveElements:
    def test_move_habitas_updates_position(self):
        m = blank()
        ops.place_habitas(m, 1, 1)
        assert ops.move_habitas(m, 0, (5, 5)) is True
        assert m.habitas_points[0] == (5, 5)

    def test_move_habitas_out_of_bounds_rejected(self):
        m = blank()
        ops.place_habitas(m, 1, 1)
        assert ops.move_habitas(m, 0, (-1, -1)) is False
        assert m.habitas_points[0] == (1, 1)  # unchanged

    def test_move_azn_updates_position(self):
        m = blank()
        ops.place_azn(m, 1, 1)
        ops.move_azn(m, 0, (6, 6))
        assert m.azn_nodes[0]["position"] == (6, 6)

    def test_set_azn_quantity(self):
        m = blank()
        ops.place_azn(m, 1, 1, quantity=10)
        ops.set_azn_quantity(m, 0, 500)
        assert m.azn_nodes[0]["quantity"] == 500

    def test_move_zone_by_offset(self):
        m = blank()
        ops.place_zone(m, (0, 0, 3, 3))
        assert ops.move_zone(m, 0, (2, 2)) is True
        assert m.injection_zones[0]["rect"] == (2, 2, 3, 3)

    def test_move_zone_rejected_if_it_would_leave_bounds(self):
        m = blank(10, 10)
        ops.place_zone(m, (7, 7, 3, 3))
        assert ops.move_zone(m, 0, (5, 5)) is False  # would push to (12,12), out of a 10x10 map
        assert m.injection_zones[0]["rect"] == (7, 7, 3, 3)  # unchanged


class TestZoneCornerResize:
    def test_detect_each_corner(self):
        m = blank()
        ops.place_zone(m, (2, 2, 4, 4))  # spans x:2-5, y:2-5
        assert ops.detect_zone_corner(m, 2, 2, 0) == "tl"
        assert ops.detect_zone_corner(m, 5, 2, 0) == "tr"
        assert ops.detect_zone_corner(m, 2, 5, 0) == "bl"
        assert ops.detect_zone_corner(m, 5, 5, 0) == "br"

    def test_detect_corner_returns_empty_string_in_the_middle(self):
        # Needs a zone large enough that its center is >1.5 cells from every
        # corner (the corner-detection radius) — a 4x4 zone is too small for
        # that to be possible at all, which is what a too-small first draft
        # of this test got wrong.
        m = blank()
        ops.place_zone(m, (2, 2, 10, 10))
        assert ops.detect_zone_corner(m, 7, 7, 0) == ""

    def test_resize_from_top_left_corner(self):
        m = blank(10, 10)
        ops.place_zone(m, (3, 3, 4, 4))  # x:3-6, y:3-6
        assert ops.resize_zone(m, 0, "tl", 2, 2) is True
        assert m.injection_zones[0]["rect"] == (2, 2, 5, 5)

    def test_resize_from_bottom_right_corner(self):
        m = blank(10, 10)
        ops.place_zone(m, (3, 3, 4, 4))
        assert ops.resize_zone(m, 0, "br", 7, 7) is True
        assert m.injection_zones[0]["rect"] == (3, 3, 5, 5)

    def test_resize_below_minimum_size_is_rejected(self):
        m = blank(10, 10)
        ops.place_zone(m, (3, 3, 4, 4))
        # Shrinking to a width of 1 via the top-left corner should be rejected (min size 2).
        assert ops.resize_zone(m, 0, "tl", 6, 3) is False
        assert m.injection_zones[0]["rect"] == (3, 3, 4, 4)  # unchanged

    def test_resize_out_of_bounds_is_rejected(self):
        m = blank(10, 10)
        ops.place_zone(m, (3, 3, 4, 4))
        assert ops.resize_zone(m, 0, "br", 99, 99) is False
        assert m.injection_zones[0]["rect"] == (3, 3, 4, 4)

    def test_resize_with_invalid_corner_name_is_rejected(self):
        m = blank(10, 10)
        ops.place_zone(m, (3, 3, 4, 4))
        assert ops.resize_zone(m, 0, "nonsense", 5, 5) is False


class TestSnapshotRestore:
    def test_snapshot_then_restore_recovers_terrain(self):
        m = blank()
        ops.paint_cell(m, 1, 1, Density.HIGH)
        snap = ops.snapshot(m)
        ops.paint_cell(m, 1, 1, Density.BONE)
        ops.restore(m, snap)
        assert m.get_cell(1, 1)["density"] == Density.HIGH

    def test_snapshot_then_restore_recovers_habitas(self):
        # This is the specific bug the Godot port's undo had for its whole
        # lifetime: habitas/AZN/zone mutations were never actually
        # recoverable via undo because only `cells` was ever snapshotted.
        m = blank()
        snap = ops.snapshot(m)  # before placing anything
        ops.place_habitas(m, 3, 3)
        assert m.habitas_points == [(3, 3)]
        ops.restore(m, snap)
        assert m.habitas_points == []

    def test_snapshot_then_restore_recovers_azn(self):
        m = blank()
        snap = ops.snapshot(m)
        ops.place_azn(m, 3, 3, quantity=40)
        ops.restore(m, snap)
        assert m.azn_nodes == []

    def test_snapshot_then_restore_recovers_zones(self):
        m = blank()
        snap = ops.snapshot(m)
        ops.place_zone(m, (1, 1, 2, 2))
        ops.restore(m, snap)
        assert m.injection_zones == []

    def test_snapshot_is_a_deep_copy_not_a_reference(self):
        m = blank()
        ops.place_azn(m, 3, 3, quantity=10)
        snap = ops.snapshot(m)
        m.azn_nodes[0]["quantity"] = 999  # mutate the live document...
        assert snap["azn_nodes"][0]["quantity"] == 10  # ...the snapshot must be unaffected

    def test_restore_recovers_width_and_height(self):
        m = blank(5, 5)
        snap = ops.snapshot(m)
        m.width, m.height = 20, 20
        ops.restore(m, snap)
        assert (m.width, m.height) == (5, 5)
