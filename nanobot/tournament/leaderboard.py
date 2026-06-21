"""Accumulates tournament results into a sorted leaderboard. Mirrors
src/tournament/leaderboard.gd."""

from __future__ import annotations

import datetime
import json
import os


class Leaderboard:
    def __init__(self):
        self._entries: dict[str, dict] = {}  # strategy_path -> entry dict

    def add_result(self, result: dict) -> None:
        if "error" in result:
            return

        a = result["player_a"]
        b = result["player_b"]
        wid = int(result.get("winner_id", -1))
        scores = result.get("final_scores", {})
        dq_a = result.get("dq_a", False)
        dq_b = result.get("dq_b", False)

        self._ensure(a, dq_a)
        self._ensure(b, dq_b)

        self._entries[a]["matches"] += 1
        self._entries[b]["matches"] += 1
        self._entries[a]["points"] += int(scores.get("0", scores.get(0, 0)))
        self._entries[b]["points"] += int(scores.get("1", scores.get(1, 0)))

        if dq_a and not dq_b:
            self._entries[b]["wins"] += 1
            self._entries[a]["losses"] += 1
        elif dq_b and not dq_a:
            self._entries[a]["wins"] += 1
            self._entries[b]["losses"] += 1
        elif wid == 0:
            self._entries[a]["wins"] += 1
            self._entries[b]["losses"] += 1
        elif wid == 1:
            self._entries[b]["wins"] += 1
            self._entries[a]["losses"] += 1
        else:
            self._entries[a]["draws"] += 1
            self._entries[b]["draws"] += 1

    def get_sorted(self) -> list[dict]:
        entries = list(self._entries.values())
        entries.sort(key=lambda e: (-e["wins"], -e["points"]))
        return entries

    def save_to_file(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "generated": datetime.datetime.now().isoformat(),
                "entries": self.get_sorted(),
            }, f, indent="\t")

    def _ensure(self, path: str, dq: bool) -> None:
        if path not in self._entries:
            self._entries[path] = {
                "path": path,
                "name": os.path.splitext(os.path.basename(path))[0],
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "points": 0,
                "matches": 0,
                "dq": dq,
            }
        elif dq:
            self._entries[path]["dq"] = True
