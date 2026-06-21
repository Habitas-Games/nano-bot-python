"""bot_type_registry.py is a module-level lazy-loaded cache, which makes
it slightly awkward to test in isolation — each test patches DATA_PATH
and resets the module's _loaded/_data globals so it re-reads from
scratch, rather than relying on (or polluting) whatever the real
data/bot_types.json load already cached for other tests in the suite."""

import json

import pytest

import nanobot.core.bot_type_registry as registry


@pytest.fixture(autouse=True)
def reset_registry_cache():
    """Every test starts from a clean lazy-load state and restores the
    real data afterward so later test files see the real bot_types.json
    again, not whatever a previous test pointed DATA_PATH at."""
    real_path = registry.DATA_PATH
    yield
    registry.DATA_PATH = real_path
    registry._loaded = False
    registry._data = {}


def point_at(tmp_path, content: str) -> str:
    path = tmp_path / "bot_types.json"
    path.write_text(content)
    registry.DATA_PATH = str(path)
    registry._loaded = False
    registry._data = {}
    return str(path)


class TestNormalLoading:
    def test_real_data_file_loads_known_types(self):
        registry._loaded = False
        registry._data = {}
        assert registry.is_valid_type("NanoAI")
        assert registry.is_valid_type("NanoCollector")

    def test_get_type_returns_stats_dict(self):
        registry._loaded = False
        registry._data = {}
        stats = registry.get_type("NanoCollector")
        assert stats["hp"] == 50

    def test_unknown_type_returns_empty_dict(self):
        registry._loaded = False
        registry._data = {}
        assert registry.get_type("NotARealType") == {}

    def test_all_types_lists_every_known_type(self):
        registry._loaded = False
        registry._data = {}
        types = registry.all_types()
        assert "NanoAI" in types
        assert "NanoWall" in types


class TestMissingFile:
    def test_missing_file_returns_empty_without_crashing(self, tmp_path):
        registry.DATA_PATH = str(tmp_path / "does_not_exist.json")
        registry._loaded = False
        registry._data = {}
        assert registry.get_type("NanoAI") == {}
        assert registry.is_valid_type("NanoAI") is False


class TestMalformedFile:
    def test_malformed_json_returns_empty_without_crashing(self, tmp_path):
        # The initial Python port used json.load() with no try/except here,
        # which let a corrupted data file crash with an unhandled
        # JSONDecodeError instead of failing gracefully — both the
        # Godot original (json.parse(...) != OK) and this function's own
        # missing-file branch already handled bad input cleanly.
        point_at(tmp_path, "{not valid json")
        assert registry.get_type("NanoAI") == {}
        assert registry.is_valid_type("NanoAI") is False
        assert registry.all_types() == []

    def test_valid_json_that_is_not_an_object_is_handled(self, tmp_path):
        # A JSON array parses without a JSONDecodeError but isn't a usable
        # stats table; get_type()'s internal _data.get(...) would crash
        # with an AttributeError on a list otherwise.
        point_at(tmp_path, json.dumps([1, 2, 3]))
        assert registry.get_type("NanoAI") == {}
