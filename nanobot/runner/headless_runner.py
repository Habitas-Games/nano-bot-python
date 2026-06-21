"""CLI usage (from project root):

    python run_headless.py --map maps/simple_tissue.json \\
        --strategy_a strategies/example_strategy.py \\
        --strategy_b strategies/other_strategy.py \\
        [--seed 42] [--out replays/my_match.json]

Mirrors src/runner/headless_runner.gd. Returns an exit code: 0 = success, 1 = error."""

from __future__ import annotations

import datetime
import os
import sys

from nanobot.core.map_loader import load_from_file
from nanobot.core.simulation_core import SimulationCore

DEFAULT_OUT_DIR = "replays"


def run_from_argv(argv: list[str]) -> int:
    args = _parse_args(argv)
    return _execute(args)


def _execute(args: dict) -> int:
    if "map" not in args:
        print("HeadlessRunner: --map is required")
        return 1

    map_data = load_from_file(args["map"])
    if map_data is None:
        print(f"HeadlessRunner: failed to load map: {args['map']}")
        return 1

    strategies = []
    if "strategy_a" in args:
        strategies.append(args["strategy_a"])
    if "strategy_b" in args:
        strategies.append(args["strategy_b"])
    for key in ("strategy_c", "strategy_d"):
        if key in args:
            strategies.append(args[key])

    try:
        seed_val = int(args.get("seed", 0))
    except ValueError:
        # Confirmed reachable: a typo'd --seed used to crash with a raw
        # ValueError traceback instead of a clean CLI error message, the
        # same class of issue as every other "fail loudly but cleanly on
        # bad input" fix in this version — just at the argument-parsing
        # layer instead of a file-loading one.
        print(f"HeadlessRunner: --seed must be an integer, got {args['seed']!r}")
        return 1
    sim = SimulationCore(map_data, strategies, seed_val)

    print(f"HeadlessRunner: starting match — map: {map_data.map_name}, "
          f"players: {max(len(strategies), 2)}, seed: {seed_val}")

    log = sim.run()

    out_path = args.get("out", _auto_out_path(strategies))
    saved = log.save_to_file(out_path)

    print(f"HeadlessRunner: match complete in {log.total_turns} turns")
    print(f"HeadlessRunner: winner — player {log.winner_id}")
    for pid, score in log.final_scores.items():
        print(f"  player {pid}: {score} pts")
    if saved:
        print(f"HeadlessRunner: replay saved to {out_path}")
    else:
        print(f"HeadlessRunner: failed to save replay to {out_path} (see above)")
        return 1
    return 0


def _parse_args(raw: list[str]) -> dict:
    result = {}
    i = 0
    while i < len(raw):
        key = raw[i]
        if key.startswith("--") and i + 1 < len(raw):
            result[key[2:]] = raw[i + 1]
            i += 2
        else:
            i += 1
    return result


def _auto_out_path(strategies: list[str]) -> str:
    names = [os.path.splitext(os.path.basename(s))[0] for s in strategies]
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    label = "_vs_".join(names) if names else "match"
    return os.path.join(DEFAULT_OUT_DIR, f"match_{stamp}_{label}.json")


if __name__ == "__main__":
    sys.exit(run_from_argv(sys.argv[1:]))
