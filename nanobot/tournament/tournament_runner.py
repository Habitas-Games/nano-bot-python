"""Round-robin tournament runner. Mirrors src/tournament/tournament_runner.gd.
Godot's version uses Signals for progress_updated/match_finished/tournament_finished;
this uses plain callback functions instead since Python has no built-in signal
bus — same effect, called from the background thread exactly like the
Godot version's call_deferred (the pygame UI must marshal these back to
the main thread itself if updating widgets, same caveat as call_deferred)."""

from __future__ import annotations

import os
import threading

from nanobot.core.map_loader import load_from_file
from nanobot.core.match_log import MatchLog
from nanobot.core.simulation_core import SimulationCore


class TournamentRunner:
    def __init__(self):
        self.schedule: list[dict] = []
        self.results: list[dict] = []

        self.on_progress_updated = None   # callback(completed: int, total: int)
        self.on_match_finished = None     # callback(result: dict)
        self.on_tournament_finished = None  # callback()

        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._abort = False

    def start(self, strategy_paths: list[str], map_paths: list[str]) -> None:
        self.schedule = self._build_schedule(strategy_paths, map_paths)
        self.results = []
        self._abort = False
        self._thread = threading.Thread(target=self._thread_main, args=(strategy_paths,), daemon=True)
        self._thread.start()

    def abort(self) -> None:
        self._abort = True

    def wait(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()

    # --- schedule builder ---

    @staticmethod
    def _build_schedule(strategies: list[str], maps: list[str]) -> list[dict]:
        sched = []
        seed = 0
        for m in maps:
            for i in range(len(strategies)):
                for j in range(i + 1, len(strategies)):
                    sched.append({
                        "map": m,
                        "player_a": strategies[i],
                        "player_b": strategies[j],
                        "seed": seed,
                    })
                    seed += 1
        return sched

    # --- background thread ---

    def _thread_main(self, strategy_paths: list[str]) -> None:
        total = len(self.schedule)

        for i, entry in enumerate(self.schedule):
            if self._abort:
                break

            map_data = load_from_file(entry["map"])
            if map_data is None:
                self._record_error(entry, "map_load_failed")
                if self.on_progress_updated:
                    self.on_progress_updated(i + 1, total)
                continue

            sim = SimulationCore(map_data, [entry["player_a"], entry["player_b"]], int(entry["seed"]))
            log = sim.run()

            replay_path = self._replay_path(entry, i)
            log.save_to_file(replay_path)

            result = {
                "match_index": i,
                "map": entry["map"],
                "player_a": entry["player_a"],
                "player_b": entry["player_b"],
                "winner_id": log.winner_id,
                "final_scores": log.final_scores,
                "total_turns": log.total_turns,
                "replay_path": replay_path,
                "dq_a": self._was_dq(log, 0),
                "dq_b": self._was_dq(log, 1),
            }

            with self._lock:
                self.results.append(result)

            if self.on_match_finished:
                self.on_match_finished(result)
            if self.on_progress_updated:
                self.on_progress_updated(i + 1, total)

        if self.on_tournament_finished:
            self.on_tournament_finished()

    # --- helpers ---

    @staticmethod
    def _replay_path(entry: dict, idx: int) -> str:
        a = os.path.splitext(os.path.basename(entry["player_a"]))[0]
        b = os.path.splitext(os.path.basename(entry["player_b"]))[0]
        return os.path.join("replays", f"tournament_{idx:03d}_{a}_vs_{b}.json")

    @staticmethod
    def _was_dq(log: MatchLog, player_id: int) -> bool:
        """A player is considered DQ if all their bots died before turn 10
        (a sign the strategy failed to load or immediately crashed)."""
        if not log.frames:
            return True
        early = log.frames[min(9, len(log.frames) - 1)]
        for bot in early.get("bots", []):
            if int(bot.get("owner", -1)) == player_id and bot.get("alive", False):
                return False
        return True

    def _record_error(self, entry: dict, reason: str) -> None:
        with self._lock:
            self.results.append({
                "map": entry["map"],
                "player_a": entry["player_a"],
                "player_b": entry["player_b"],
                "error": reason,
            })
