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
