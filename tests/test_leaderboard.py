import builtins

from nanobot.tournament.leaderboard import Leaderboard


def result(player_a="a.py", player_b="b.py", winner_id=0, scores=None, dq_a=False, dq_b=False):
    return {
        "player_a": player_a, "player_b": player_b, "winner_id": winner_id,
        "final_scores": scores or {0: 0, 1: 0}, "dq_a": dq_a, "dq_b": dq_b,
    }


class TestBasicScoring:
    def test_winner_gets_a_win_loser_gets_a_loss(self):
        lb = Leaderboard()
        lb.add_result(result(winner_id=0, scores={0: 50, 1: 10}))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["wins"] == 1
        assert entries["b"]["losses"] == 1

    def test_player_b_winning_credits_correctly(self):
        lb = Leaderboard()
        lb.add_result(result(winner_id=1, scores={0: 10, 1: 50}))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["b"]["wins"] == 1
        assert entries["a"]["losses"] == 1

    def test_tie_score_with_no_winner_id_is_a_draw(self):
        lb = Leaderboard()
        lb.add_result(result(winner_id=-1, scores={0: 20, 1: 20}))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["draws"] == 1
        assert entries["b"]["draws"] == 1

    def test_points_accumulate_from_final_scores(self):
        lb = Leaderboard()
        lb.add_result(result(winner_id=0, scores={0: 50, 1: 10}))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["points"] == 50
        assert entries["b"]["points"] == 10

    def test_matches_count_increments_for_both_players(self):
        lb = Leaderboard()
        lb.add_result(result())
        lb.add_result(result())
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["matches"] == 2
        assert entries["b"]["matches"] == 2

    def test_points_accumulate_across_multiple_matches(self):
        lb = Leaderboard()
        lb.add_result(result(winner_id=0, scores={0: 10, 1: 0}))
        lb.add_result(result(winner_id=0, scores={0: 15, 1: 0}))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["points"] == 25

    def test_error_result_is_skipped_entirely(self):
        lb = Leaderboard()
        lb.add_result({"error": "map_load_failed", "player_a": "a.py", "player_b": "b.py"})
        assert lb.get_sorted() == []


class TestDisqualification:
    def test_dq_a_credits_a_win_to_b(self):
        lb = Leaderboard()
        lb.add_result(result(dq_a=True))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["b"]["wins"] == 1
        assert entries["a"]["losses"] == 1

    def test_dq_flag_recorded_on_entry(self):
        lb = Leaderboard()
        lb.add_result(result(dq_a=True))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["dq"] is True
        assert entries["b"]["dq"] is False

    def test_both_dq_counts_as_a_draw_not_a_win_for_either(self):
        # Neither branch in add_result's dq handling fires when both are DQ
        # (the elif chain only special-cases "exactly one side DQ'd"), so
        # this falls through to the winner_id-based outcome.
        lb = Leaderboard()
        lb.add_result(result(winner_id=-1, dq_a=True, dq_b=True))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["draws"] == 1
        assert entries["b"]["draws"] == 1

    def test_dq_persists_once_set_even_on_a_later_non_dq_match(self):
        lb = Leaderboard()
        lb.add_result(result(dq_a=True))
        lb.add_result(result(player_a="a.py", player_b="c.py", winner_id=0, dq_a=False, dq_b=False))
        entries = {e["name"]: e for e in lb.get_sorted()}
        assert entries["a"]["dq"] is True  # once flagged, stays flagged


class TestSorting:
    def test_sorted_by_wins_descending(self):
        lb = Leaderboard()
        lb.add_result(result(player_a="winner.py", player_b="loser.py", winner_id=0))
        lb.add_result(result(player_a="loser.py", player_b="winner2.py", winner_id=1))
        names_in_order = [e["name"] for e in lb.get_sorted()]
        assert names_in_order[0] in ("winner", "winner2")
        assert names_in_order.index("loser") > 0

    def test_ties_in_wins_broken_by_points(self):
        lb = Leaderboard()
        lb.add_result(result(player_a="high.py", player_b="x.py", winner_id=0, scores={0: 100, 1: 0}))
        lb.add_result(result(player_a="low.py", player_b="y.py", winner_id=0, scores={0: 10, 1: 0}))
        names_in_order = [e["name"] for e in lb.get_sorted()]
        assert names_in_order.index("high") < names_in_order.index("low")


class TestSaveToFile:
    def test_save_creates_file_with_entries(self, tmp_path):
        import json
        lb = Leaderboard()
        lb.add_result(result(winner_id=0, scores={0: 50, 1: 10}))
        path = str(tmp_path / "results.json")
        lb.save_to_file(path)
        with open(path) as f:
            data = json.load(f)
        assert "entries" in data
        assert "generated" in data
        assert len(data["entries"]) == 2

    def test_save_creates_parent_directory(self, tmp_path):
        lb = Leaderboard()
        lb.add_result(result())
        nested = tmp_path / "a" / "b" / "results.json"
        lb.save_to_file(str(nested))
        assert nested.exists()

    def test_save_returns_true_on_success(self, tmp_path):
        lb = Leaderboard()
        assert lb.save_to_file(str(tmp_path / "results.json")) is True

    def test_save_returns_false_on_oserror_not_raises(self, tmp_path, monkeypatch):
        # Confirmed reachable, not hypothetical: TournamentScreen calls
        # this from inside the tournament-completion callback, and a
        # failure here used to make the screen claim "Saved to {path}"
        # even though the file was never written (self.finished is set
        # before this call) — see tournament_ui.py's _on_finished fix.
        lb = Leaderboard()

        def raise_oserror(*args, **kwargs):
            raise OSError("disk full (simulated)")
        monkeypatch.setattr(builtins, "open", raise_oserror)

        assert lb.save_to_file(str(tmp_path / "results.json")) is False
