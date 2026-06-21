"""Per-turn snapshot recorder + JSON export/import. Mirrors src/core/match_log.gd."""

from __future__ import annotations

import json
import os

from nanobot.core.nanobot_data import NanoBotData


class MatchLog:
    def __init__(self):
        self.map_name = ""
        self.player_strategies: list[str] = []
        self.frames: list[dict] = []
        self.final_scores: dict = {}
        self.winner_id = -1
        self.total_turns = 0

    def record_frame(self, turn: int, scores: dict, bots: list[NanoBotData],
                      azn_nodes: list[dict], habitas_points: list[dict], events: list[dict]) -> None:
        self.frames.append({
            "turn": turn,
            "scores": dict(scores),
            "bots": self._serialize_bots(bots),
            "azn_nodes": self._serialize_azn(azn_nodes),
            "habitas_points": self._serialize_habitas(habitas_points),
            "events": list(events),
        })

    def save_to_file(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent="\t")

    def to_dict(self) -> dict:
        return {
            "map_name": self.map_name,
            "player_strategies": self.player_strategies,
            "total_turns": self.total_turns,
            "final_scores": self.final_scores,
            "winner_id": self.winner_id,
            "frames": self.frames,
        }

    @staticmethod
    def load_from_file(path: str) -> "MatchLog | None":
        if not os.path.exists(path):
            print(f"MatchLog: file not found: {path}")
            return None
        with open(path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"MatchLog: JSON parse error in {path}: {e}")
                return None
        if not isinstance(data, dict):
            # Syntactically valid JSON that isn't an object (e.g. a bare
            # array) parses without error but every data.get(...) call
            # below would crash with an AttributeError on first use. This
            # path matters more here than in most of this codebase's other
            # loaders: it's reachable directly from the playback viewer
            # opening a corrupted/incomplete replay file through the real
            # UI, not just from hand-edited input.
            print(f"MatchLog: expected a JSON object in {path}, got {type(data).__name__}")
            return None
        log = MatchLog()
        log.map_name = data.get("map_name", "")
        log.player_strategies = data.get("player_strategies", [])
        log.total_turns = int(data.get("total_turns", 0))
        log.final_scores = data.get("final_scores", {})
        log.winner_id = int(data.get("winner_id", -1))
        log.frames = data.get("frames", [])
        return log

    @staticmethod
    def _serialize_bots(bots: list[NanoBotData]) -> list[dict]:
        return [b.to_log_dict() for b in bots]

    @staticmethod
    def _serialize_azn(nodes: list[dict]) -> list[dict]:
        return [{"pos": [n["position"][0], n["position"][1]], "qty": n["quantity"]} for n in nodes]

    @staticmethod
    def _serialize_habitas(points: list[dict]) -> list[dict]:
        return [
            {"pos": [hp["position"][0], hp["position"][1]], "owner": hp["owner"], "azn": hp["azn_stored"]}
            for hp in points
        ]
