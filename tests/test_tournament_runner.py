"""TournamentRunner runs matches on a background thread — an unhandled
exception there doesn't crash the app, it just silently kills the
thread. Confirmed directly before fixing: on_tournament_finished never
fired, self.results stayed empty, and a screen watching this runner's
progress would show a permanently frozen progress bar with no error and
no way to tell the tournament had actually stopped. These tests cover
the schedule builder and that failure-isolation fix specifically —
real end-to-end match runs are covered by the headless-CLI checks
elsewhere, not duplicated here."""

import unittest.mock as mock

from nanobot.core.simulation_core import SimulationCore
from nanobot.tournament.tournament_runner import TournamentRunner


class TestBuildSchedule:
    def test_round_robin_size_for_n_strategies(self):
        strategies = ["a.py", "b.py", "c.py", "d.py"]
        sched = TournamentRunner._build_schedule(strategies, ["map.json"])
        assert len(sched) == 6  # n*(n-1)/2 for n=4

    def test_every_pair_appears_exactly_once_per_map(self):
        strategies = ["a.py", "b.py", "c.py"]
        sched = TournamentRunner._build_schedule(strategies, ["map.json"])
        pairs = {(e["player_a"], e["player_b"]) for e in sched}
        assert pairs == {("a.py", "b.py"), ("a.py", "c.py"), ("b.py", "c.py")}

    def test_schedule_scales_with_map_count(self):
        sched = TournamentRunner._build_schedule(["a.py", "b.py"], ["m1.json", "m2.json", "m3.json"])
        assert len(sched) == 3  # one pairing x 3 maps

    def test_seeds_are_unique_and_sequential(self):
        sched = TournamentRunner._build_schedule(["a.py", "b.py", "c.py"], ["m1.json", "m2.json"])
        seeds = [e["seed"] for e in sched]
        assert seeds == list(range(len(sched)))

    def test_single_strategy_produces_empty_schedule(self):
        assert TournamentRunner._build_schedule(["a.py"], ["map.json"]) == []


class TestFailureIsolation:
    def test_an_exception_in_one_match_does_not_kill_the_background_thread(self):
        runner = TournamentRunner()
        finished = []
        runner.on_tournament_finished = lambda: finished.append(True)

        with mock.patch.object(SimulationCore, "run", side_effect=RuntimeError("boom")):
            runner.start(["strategies/example_strategy.py", "strategies/example_strategy_v2.py"],
                         ["maps/simple_tissue.json"])
            runner.wait()

        assert not runner._thread.is_alive()
        assert finished == [True]

    def test_failed_match_is_recorded_as_an_error_result(self):
        runner = TournamentRunner()
        with mock.patch.object(SimulationCore, "run", side_effect=RuntimeError("boom")):
            runner.start(["strategies/example_strategy.py", "strategies/example_strategy_v2.py"],
                         ["maps/simple_tissue.json"])
            runner.wait()

        assert len(runner.results) == 1
        assert "error" in runner.results[0]
        assert "boom" in runner.results[0]["error"]

    def test_progress_callback_still_fires_for_a_failed_match(self):
        runner = TournamentRunner()
        progress_calls = []
        runner.on_progress_updated = lambda completed, total: progress_calls.append((completed, total))

        with mock.patch.object(SimulationCore, "run", side_effect=RuntimeError("boom")):
            runner.start(["strategies/example_strategy.py", "strategies/example_strategy_v2.py"],
                         ["maps/simple_tissue.json"])
            runner.wait()

        assert progress_calls == [(1, 1)]

    def test_tournament_continues_to_later_matches_after_one_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "replays").mkdir()

        runner = TournamentRunner()
        real_run = SimulationCore.run
        call_count = {"n": 0}

        def flaky_run(self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("fails only on the first match")
            return real_run(self)

        strategies_dir = "/home/mario/godot/nano-bot-python/strategies"
        maps_dir = "/home/mario/godot/nano-bot-python/maps"
        with mock.patch.object(SimulationCore, "run", flaky_run):
            runner.start(
                [f"{strategies_dir}/example_strategy.py", f"{strategies_dir}/example_strategy_v2.py"],
                [f"{maps_dir}/simple_tissue.json", f"{maps_dir}/vascular_network.json"],
            )
            runner.wait()

        assert len(runner.results) == 2
        assert "error" in runner.results[0]
        assert "error" not in runner.results[1]  # the second match ran normally
