"""MatchLog.load_from_file() is the replay-loading path used directly by
the playback viewer — a crash here is reachable from a user opening a
corrupted or incomplete replay file through the real UI, not just from
hand-edited input, which makes its error handling worth covering
directly rather than only incidentally via the viewer's own checks."""

import builtins
import json

from nanobot.core.nanobot_data import NanoBotData
from nanobot.core.match_log import MatchLog


class TestRecordFrame:
    def test_record_frame_serializes_bots_azn_habitas(self):
        log = MatchLog()
        bot = NanoBotData(1, 0, "NanoAI", (3, 3), {"hp": 20})
        log.record_frame(
            turn=1, scores={0: 5, 1: 0}, bots=[bot],
            azn_nodes=[{"position": (1, 1), "quantity": 10}],
            habitas_points=[{"position": (2, 2), "owner": 0, "azn_stored": 0}],
            events=[{"type": "move"}],
        )
        frame = log.frames[0]
        assert frame["turn"] == 1
        assert frame["bots"][0]["id"] == 1
        assert frame["azn_nodes"][0]["pos"] == [1, 1]
        assert frame["habitas_points"][0]["pos"] == [2, 2]
        assert frame["events"] == [{"type": "move"}]


class TestSaveAndRoundTrip:
    def test_save_and_reload_round_trips(self, tmp_path):
        log = MatchLog()
        log.map_name = "Test Map"
        log.player_strategies = ["a.py", "b.py"]
        log.total_turns = 42
        log.final_scores = {0: 10, 1: 20}
        log.winner_id = 1
        bot = NanoBotData(1, 0, "NanoAI", (1, 1), {"hp": 20})
        log.record_frame(1, {0: 0, 1: 0}, [bot], [], [], [])

        path = str(tmp_path / "replay.json")
        log.save_to_file(path)
        reloaded = MatchLog.load_from_file(path)

        assert reloaded.map_name == "Test Map"
        assert reloaded.total_turns == 42
        assert reloaded.winner_id == 1
        assert len(reloaded.frames) == 1

    def test_save_creates_parent_directory(self, tmp_path):
        log = MatchLog()
        nested = tmp_path / "a" / "b" / "replay.json"
        log.save_to_file(str(nested))
        assert nested.exists()

    def test_save_returns_true_on_success(self, tmp_path):
        log = MatchLog()
        assert log.save_to_file(str(tmp_path / "replay.json")) is True

    def test_save_returns_false_on_oserror_not_raises(self, tmp_path, monkeypatch):
        # Confirmed reachable, not hypothetical: TournamentRunner calls
        # this from a background thread, where an unhandled OSError used
        # to propagate out and silently kill the thread (see
        # tournament_runner.py's _run_one_match fix in the same version).
        log = MatchLog()

        def raise_oserror(*args, **kwargs):
            raise OSError("disk full (simulated)")
        monkeypatch.setattr(builtins, "open", raise_oserror)

        assert log.save_to_file(str(tmp_path / "replay.json")) is False


class TestLoadErrorHandling:
    def test_nonexistent_file_returns_none(self):
        assert MatchLog.load_from_file("/nonexistent/replay.json") is None

    def test_malformed_json_returns_none_not_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json")
        assert MatchLog.load_from_file(str(path)) is None

    def test_valid_json_array_returns_none_not_raises(self, tmp_path):
        # Syntactically valid JSON that isn't an object parses without a
        # JSONDecodeError but every data.get(...) call would crash with
        # an AttributeError on a list otherwise.
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps([1, 2, 3]))
        assert MatchLog.load_from_file(str(path)) is None

    def test_valid_json_string_returns_none_not_raises(self, tmp_path):
        path = tmp_path / "wrong_shape.json"
        path.write_text(json.dumps("just a string"))
        assert MatchLog.load_from_file(str(path)) is None

    def test_missing_optional_fields_use_defaults(self, tmp_path):
        path = tmp_path / "minimal.json"
        path.write_text(json.dumps({}))
        log = MatchLog.load_from_file(str(path))
        assert log is not None
        assert log.map_name == ""
        assert log.total_turns == 0
        assert log.winner_id == -1
        assert log.frames == []
