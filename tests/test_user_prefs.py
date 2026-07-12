"""Unit tests for nanobot.core.user_prefs — the persistence must be
failure-tolerant in every direction (missing, corrupt, wrong-shape,
unwritable), because preferences are a convenience, never a crash."""

import json

import pytest

from nanobot.core import user_prefs


@pytest.fixture
def prefs_file(tmp_path, monkeypatch):
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(user_prefs, "PREFS_PATH", str(path))
    return path


class TestRoundTrip:
    def test_update_then_get(self, prefs_file):
        user_prefs.update(last_map="maps/bone_maze.json")
        assert user_prefs.get("last_map") == "maps/bone_maze.json"

    def test_update_merges_instead_of_replacing(self, prefs_file):
        user_prefs.update(last_map="a.json")
        user_prefs.update(last_strategy_dir="/tmp")
        assert user_prefs.get("last_map") == "a.json"
        assert user_prefs.get("last_strategy_dir") == "/tmp"


class TestFailureTolerance:
    def test_missing_file_returns_defaults(self, prefs_file):
        assert user_prefs.load() == {}
        assert user_prefs.get("last_map", "fallback") == "fallback"

    def test_corrupt_json_returns_defaults_not_raises(self, prefs_file):
        prefs_file.write_text("{not json!")
        assert user_prefs.load() == {}

    def test_non_object_json_returns_defaults(self, prefs_file):
        prefs_file.write_text(json.dumps(["a", "list"]))
        assert user_prefs.load() == {}


class TestExistenceFilters:
    def test_existing_file_filters_stale_paths(self, prefs_file, tmp_path):
        real = tmp_path / "real.py"
        real.write_text("# hi")
        user_prefs.update(last_map=str(real))
        assert user_prefs.existing_file("last_map") == str(real)
        real.unlink()
        assert user_prefs.existing_file("last_map") is None

    def test_existing_files_drops_only_the_stale_ones(self, prefs_file, tmp_path):
        a = tmp_path / "a.py"
        a.write_text("")
        user_prefs.update(last_strategies=[str(a), str(tmp_path / "gone.py")])
        assert user_prefs.existing_files("last_strategies") == [str(a)]

    def test_existing_files_tolerates_wrong_shape(self, prefs_file):
        user_prefs.update(last_strategies="not-a-list")
        assert user_prefs.existing_files("last_strategies") == []

    def test_existing_dir_falls_back_when_stale(self, prefs_file, tmp_path):
        user_prefs.update(last_map_dir=str(tmp_path))
        assert user_prefs.existing_dir("last_map_dir", "/fallback") == str(tmp_path)
        user_prefs.update(last_map_dir=str(tmp_path / "deleted"))
        assert user_prefs.existing_dir("last_map_dir", "/fallback") == "/fallback"
