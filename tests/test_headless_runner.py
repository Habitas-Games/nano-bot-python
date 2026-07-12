"""headless_runner.py is the CLI entry point — its argument parsing and
error paths are exactly what a participant typo's a command against, so
they're worth covering directly rather than only via ad hoc manual CLI
invocations."""

from nanobot.runner.headless_runner import _execute, _parse_args


class TestParseArgs:
    def test_parses_key_value_pairs(self):
        args = _parse_args(["--map", "maps/m.json", "--seed", "42"])
        assert args == {"map": "maps/m.json", "seed": "42"}

    def test_empty_argv_returns_empty_dict(self):
        assert _parse_args([]) == {}

    def test_dangling_flag_with_no_value_is_ignored(self):
        # The last --map has no following value, so it can't be consumed
        # as a key; this must not raise an IndexError.
        args = _parse_args(["--seed", "1", "--map"])
        assert args == {"seed": "1"}


class TestExecuteErrorPaths:
    def test_missing_map_argument_fails_cleanly(self):
        assert _execute({"strategy_a": "a.py", "strategy_b": "b.py"}) == 1

    def test_nonexistent_map_file_fails_cleanly(self):
        assert _execute({"map": "/nonexistent/map.json"}) == 1

    def test_non_integer_seed_fails_cleanly_not_raises(self):
        # Confirmed reachable: this used to crash with an unhandled
        # ValueError and a raw traceback instead of a clean CLI error,
        # the same class of fix as every other "fail loudly but cleanly
        # on bad input" change in this version.
        result = _execute({
            "map": "maps/bone_maze.json",
            "strategy_a": "strategies/example_strategy.py",
            "strategy_b": "strategies/example_strategy_v2.py",
            "seed": "not_a_number",
        })
        assert result == 1

    def test_valid_run_with_explicit_seed_succeeds(self, tmp_path):
        out_path = str(tmp_path / "replay.json")
        result = _execute({
            "map": "maps/bone_maze.json",
            "strategy_a": "strategies/example_strategy.py",
            "strategy_b": "strategies/example_strategy_v2.py",
            "seed": "7",
            "out": out_path,
        })
        assert result == 0
        import os
        assert os.path.exists(out_path)
