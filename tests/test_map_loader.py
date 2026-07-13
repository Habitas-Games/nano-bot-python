"""map_loader is the single canonical home for JSON <-> MapData in both
directions (see analysis.md §3) — the whole reason that consolidation
exists is to avoid the Godot project's duplicate-loader bug, so the
round-trip property (load(save(x)) == x) is the most important thing to
verify here, plus the "required fields" behavior that was deliberately
made stricter than either of the two pre-port implementations guessed."""

import json
import os

import pytest

from nanobot.core import map_loader
from nanobot.core.map_data import Density, MapData, StreamDir


@pytest.fixture
def populated_map():
    m = MapData(10, 10)
    m.map_name = "Test Map"
    m._cells[5 * 10 + 5]["density"] = Density.HIGH
    m._cells[3 * 10 + 2]["stream_dir"] = StreamDir.EAST
    m.habitas_points.append((1, 1))
    m.habitas_points.append((8, 8))
    m.azn_nodes.append({"position": (4, 4), "quantity": 25})
    m.injection_zones.append({"player": 0, "rect": (0, 0, 3, 3)})
    m.injection_zones.append({"player": 1, "rect": (7, 7, 3, 3)})
    return m


class TestConversionHelpers:
    @pytest.mark.parametrize("density,s", [
        (Density.LOW, "low"), (Density.MEDIUM, "medium"),
        (Density.HIGH, "high"), (Density.BONE, "bone"),
    ])
    def test_density_string_round_trip(self, density, s):
        assert map_loader.density_to_string(density) == s
        assert map_loader.string_to_density(s) == density

    def test_string_to_density_is_case_insensitive(self):
        assert map_loader.string_to_density("HIGH") == Density.HIGH
        assert map_loader.string_to_density("High") == Density.HIGH

    def test_unknown_density_string_defaults_to_low(self):
        assert map_loader.string_to_density("nonsense") == Density.LOW

    @pytest.mark.parametrize("stream,s", [
        (StreamDir.NORTH, "north"), (StreamDir.SOUTH, "south"),
        (StreamDir.EAST, "east"), (StreamDir.WEST, "west"),
    ])
    def test_stream_string_round_trip(self, stream, s):
        assert map_loader.stream_to_string(stream) == s
        assert map_loader.string_to_stream(s) == stream

    def test_none_stream_has_no_string_representation(self):
        # NONE is the implicit default and is never written to JSON (sparse
        # encoding — see create_json) so its string form is just "".
        assert map_loader.stream_to_string(StreamDir.NONE) == ""

    def test_empty_stream_string_means_none(self):
        assert map_loader.string_to_stream("") == StreamDir.NONE


class TestRequiredFields:
    def test_missing_width_returns_none(self):
        assert map_loader._parse({"height": 10}, "x") is None

    def test_missing_height_returns_none(self):
        assert map_loader._parse({"width": 10}, "x") is None

    def test_missing_both_returns_none(self):
        assert map_loader._parse({"name": "no dims"}, "x") is None

    def test_present_width_and_height_succeeds(self):
        m = map_loader._parse({"width": 3, "height": 4}, "x")
        assert m is not None
        assert (m.width, m.height) == (3, 4)

    def test_numeric_string_dimensions_are_accepted(self):
        # JSON authored/edited by hand sometimes quotes numbers — int() on
        # a numeric string works fine and shouldn't be rejected.
        m = map_loader._parse({"width": "10", "height": "10"}, "x")
        assert m is not None
        assert (m.width, m.height) == (10, 10)

    def test_negative_width_is_rejected(self):
        # A previous version silently accepted this and produced a
        # MapData with width=-5 but 0 actual cells (range(-5*10) is
        # empty) — every coordinate would then be incorrectly reported
        # out of bounds. Reject it outright instead.
        assert map_loader._parse({"width": -5, "height": 10}, "x") is None

    def test_zero_width_is_rejected(self):
        assert map_loader._parse({"width": 0, "height": 10}, "x") is None

    def test_zero_height_is_rejected(self):
        assert map_loader._parse({"width": 10, "height": 0}, "x") is None

    def test_non_numeric_width_is_rejected_cleanly(self):
        assert map_loader._parse({"width": "not_a_number", "height": 10}, "x") is None

    def test_malformed_cell_entry_is_rejected_cleanly_not_raised(self):
        # A previous version let this raise an unhandled ValueError out of
        # the loader instead of failing the same way every other malformed-
        # input case in this function does.
        result = map_loader._parse(
            {"width": 10, "height": 10, "cells": [{"x": "not_a_number", "y": 5, "density": "low"}]},
            "x",
        )
        assert result is None

    def test_malformed_habitas_entry_is_rejected_cleanly(self):
        result = map_loader._parse(
            {"width": 10, "height": 10, "habitas_points": [{"x": "bad"}]}, "x")
        assert result is None

    def test_habitas_entry_missing_required_key_is_rejected_cleanly(self):
        result = map_loader._parse(
            {"width": 10, "height": 10, "habitas_points": [{"x": 1}]}, "x")  # no "y"
        assert result is None


class TestLoadFromFile:
    def test_nonexistent_file_returns_none(self):
        assert map_loader.load_from_file("/nonexistent/path/map.json") is None

    def test_invalid_json_returns_none(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        assert map_loader.load_from_file(str(bad)) is None

    def test_default_density_applies_to_unlisted_cells(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({
            "width": 3, "height": 3, "default_density": "high", "cells": [],
        }))
        m = map_loader.load_from_file(str(path))
        assert all(c["density"] == Density.HIGH for c in m._cells)

    def test_explicit_cells_override_default_density(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({
            "width": 3, "height": 3, "default_density": "low",
            "cells": [{"x": 1, "y": 1, "density": "bone"}],
        }))
        m = map_loader.load_from_file(str(path))
        assert m.get_cell(1, 1)["density"] == Density.BONE
        assert m.get_cell(0, 0)["density"] == Density.LOW

    def test_out_of_bounds_cell_entries_are_silently_skipped(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({
            "width": 2, "height": 2,
            "cells": [{"x": 99, "y": 99, "density": "high"}],
        }))
        m = map_loader.load_from_file(str(path))
        assert m is not None  # must not crash on an out-of-range cell

    def test_zone_rect_converts_x1y1x2y2_to_xywh_inclusive(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({
            "width": 10, "height": 10,
            "injection_zones": [{"player": 0, "x1": 2, "y1": 3, "x2": 5, "y2": 4}],
        }))
        m = map_loader.load_from_file(str(path))
        # x1..x2 inclusive spans 4 cells (2,3,4,5); y1..y2 inclusive spans 2 cells (3,4)
        assert m.injection_zones[0]["rect"] == (2, 3, 4, 2)

    def test_custom_starting_azn_is_read_from_the_map(self, tmp_path):
        # Previously this field was write-only: MapData had no such
        # attribute at all, so a map declaring a non-default budget had it
        # silently discarded on load.
        path = tmp_path / "m.json"
        path.write_text(json.dumps({"width": 5, "height": 5, "starting_azn": 999}))
        m = map_loader.load_from_file(str(path))
        assert m.starting_azn == 999

    def test_missing_starting_azn_defaults_to_150(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps({"width": 5, "height": 5}))
        m = map_loader.load_from_file(str(path))
        assert m.starting_azn == 150


class TestSaveAndRoundTrip:
    def test_save_creates_file(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        assert map_loader.save_to_file(populated_map, path)
        assert os.path.exists(path)

    def test_round_trip_preserves_dimensions(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert (reloaded.width, reloaded.height) == (populated_map.width, populated_map.height)

    def test_round_trip_preserves_custom_starting_azn(self, populated_map, tmp_path):
        populated_map.starting_azn = 275
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.starting_azn == 275

    def test_save_starting_azn_parameter_overrides_the_maps_own_value(self, populated_map, tmp_path):
        populated_map.starting_azn = 275
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path, starting_azn=50)  # explicit override
        reloaded = map_loader.load_from_file(path)
        assert reloaded.starting_azn == 50

    def test_round_trip_preserves_habitas_points(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert sorted(reloaded.habitas_points) == sorted(populated_map.habitas_points)

    def test_round_trip_preserves_azn_nodes(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.azn_nodes == populated_map.azn_nodes

    def test_round_trip_preserves_injection_zones(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.injection_zones == populated_map.injection_zones

    def test_round_trip_preserves_non_default_terrain(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.get_cell(5, 5)["density"] == Density.HIGH
        assert reloaded.get_cell(2, 3)["stream_dir"] == StreamDir.EAST

    def test_round_trip_preserves_default_terrain(self, populated_map, tmp_path):
        path = str(tmp_path / "out.json")
        map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.get_cell(0, 0)["density"] == Density.LOW

    def test_sparse_encoding_only_lists_non_default_cells(self, populated_map):
        data = map_loader.create_json(populated_map)
        # Only 2 cells were set to non-default (one density change, one stream).
        assert len(data["cells"]) == 2

    def test_save_creates_parent_directory(self, populated_map, tmp_path):
        nested = tmp_path / "a" / "b" / "c.json"
        assert map_loader.save_to_file(populated_map, str(nested))
        assert nested.exists()


class TestValidate:
    def test_blank_map_has_three_errors(self):
        m = MapData(5, 5)
        errors = map_loader.validate(m)
        assert len(errors) == 3

    def test_fully_populated_map_has_no_errors(self, populated_map):
        assert map_loader.validate(populated_map) == []

    def test_missing_only_habitas_reports_one_error(self, populated_map):
        populated_map.habitas_points.clear()
        errors = map_loader.validate(populated_map)
        assert len(errors) == 1
        assert "Habitas" in errors[0]


class TestValidatePassability:
    def test_habitas_on_bone_is_an_error(self, populated_map):
        x, y = populated_map.habitas_points[0]
        populated_map.set_cell(x, y, Density.BONE, StreamDir.NONE)
        errors = map_loader.validate(populated_map)
        assert any("Habitas" in e and "impassable" in e for e in errors)

    def test_azn_on_bone_is_an_error(self, populated_map):
        x, y = populated_map.azn_nodes[0]["position"]
        populated_map.set_cell(x, y, Density.BONE, StreamDir.NONE)
        errors = map_loader.validate(populated_map)
        assert any("AZN" in e and "impassable" in e for e in errors)

    def test_fully_boned_zone_is_an_error(self, populated_map):
        rx, ry, rw, rh = populated_map.injection_zones[0]["rect"]
        for dx in range(rw):
            for dy in range(rh):
                populated_map.set_cell(rx + dx, ry + dy, Density.BONE, StreamDir.NONE)
        errors = map_loader.validate(populated_map)
        assert any("injection zone" in e for e in errors)

    def test_hazard_waypoint_on_bone_is_an_error(self, populated_map):
        populated_map.hazards.append(
            {"path": [(0, 0)], "hp": 40, "damage": 3, "range": 1.5, "move_every": 2})
        populated_map.set_cell(0, 0, Density.BONE, StreamDir.NONE)
        errors = map_loader.validate(populated_map)
        assert any("White cell" in e for e in errors)


class TestDeriveMapName:
    def test_underscores_become_title_case(self):
        assert map_loader.derive_map_name("bone_maze.json") == "Bone Maze"

    def test_full_path_and_hyphens(self):
        assert map_loader.derive_map_name("/tmp/maps/my-cool_map.json") == "My Cool Map"

    def test_empty_stem_falls_back(self):
        assert map_loader.derive_map_name(".json") == "Untitled Map"


class TestBonusHoldAll:
    def test_default_is_zero(self, populated_map):
        assert populated_map.bonus_hold_all == 0

    def test_round_trips_when_set(self, tmp_path, populated_map):
        populated_map.bonus_hold_all = 50
        path = str(tmp_path / "m.json")
        assert map_loader.save_to_file(populated_map, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded.bonus_hold_all == 50

    def test_omitted_from_json_when_zero(self, populated_map):
        j = map_loader.create_json(populated_map)
        assert "bonus_hold_all" not in j

    def test_negative_values_clamp_to_zero_on_load(self, tmp_path, populated_map):
        path = str(tmp_path / "m.json")
        map_loader.save_to_file(populated_map, path)
        import json as _json
        data = _json.load(open(path))
        data["bonus_hold_all"] = -10
        _json.dump(data, open(path, "w"))
        assert map_loader.load_from_file(path).bonus_hold_all == 0
