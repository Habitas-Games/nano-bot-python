#!/usr/bin/env python3
"""CLI tournament entry point: round-robin all strategies in --strategies
across all maps in --maps, then print + save a leaderboard."""

import argparse
import glob
import sys

from nanobot.tournament.leaderboard import Leaderboard
from nanobot.tournament.tournament_runner import TournamentRunner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategies", default="strategies/*.py")
    parser.add_argument("--maps", default="maps/*.json")
    parser.add_argument("--out", default="replays/tournament_results.json")
    args = parser.parse_args()

    strategy_paths = sorted(glob.glob(args.strategies))
    map_paths = sorted(glob.glob(args.maps))

    if len(strategy_paths) < 2:
        print(f"Need at least 2 strategies, found {len(strategy_paths)}: {strategy_paths}")
        return 1
    if not map_paths:
        print("No maps found")
        return 1

    print(f"Tournament: {len(strategy_paths)} strategies x {len(map_paths)} maps")
    for s in strategy_paths:
        print(f"  strategy: {s}")
    for m in map_paths:
        print(f"  map: {m}")

    leaderboard = Leaderboard()
    runner = TournamentRunner()

    def on_progress(completed: int, total: int) -> None:
        print(f"  [{completed}/{total}] matches complete")

    def on_match_finished(result: dict) -> None:
        leaderboard.add_result(result)

    runner.on_progress_updated = on_progress
    runner.on_match_finished = on_match_finished

    runner.start(strategy_paths, map_paths)
    runner.wait()

    saved = leaderboard.save_to_file(args.out)

    print("\n=== Leaderboard ===")
    for i, entry in enumerate(leaderboard.get_sorted(), start=1):
        dq_flag = " (DQ)" if entry["dq"] else ""
        print(f"{i}. {entry['name']}{dq_flag} — {entry['wins']}W {entry['losses']}L "
              f"{entry['draws']}D, {entry['points']} pts over {entry['matches']} matches")

    if saved:
        print(f"\nSaved leaderboard to {args.out}")
    else:
        print(f"\nFailed to save leaderboard to {args.out} (see above)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
