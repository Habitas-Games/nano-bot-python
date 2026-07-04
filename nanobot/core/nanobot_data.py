"""Runtime state for one nanobot instance. Mirrors src/core/nanobot_data.gd."""

from __future__ import annotations

from nanobot.core.action_request import ActionRequest


class NanoBotData:
    def __init__(self, bot_id: int, owner_id: int, bot_type: str,
                 position: tuple[int, int], stats: dict):
        self.id = bot_id
        self.owner_id = owner_id
        self.type = bot_type
        self.position = position
        self.hp = int(stats.get("hp", 20))
        self.max_hp = self.hp
        self.azn_carried = 0
        self.turns_until_move = 0
        self.path_remaining: list[tuple[int, int]] = []
        self.cached_target: tuple[int, int] = (-1, -1)
        self.is_alive = True
        self.pending_action: ActionRequest | None = None
        self.auto_destruct_countdown = -1  # -1 = disabled
        self.is_stationary = bool(stats.get("stationary", False))
        self.density_immune = bool(stats.get("density_immune", False))
        self.traversal_penalty = int(stats.get("traversal_penalty", 0))
        self.scan = int(stats.get("scan", 0))
        if "auto_destruct_turns" in stats:
            self.auto_destruct_countdown = int(stats["auto_destruct_turns"])

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.is_alive = False

    def to_log_dict(self) -> dict:
        return {
            "id": self.id,
            "owner": self.owner_id,
            "type": self.type,
            "pos": [self.position[0], self.position[1]],
            "hp": self.hp,
            "azn": self.azn_carried,
            "alive": self.is_alive,
            "action": self.pending_action.type_name() if self.pending_action else "none",
        }
