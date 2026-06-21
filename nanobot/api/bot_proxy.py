"""Read-only bot snapshot + action queue exposed to participant code.
Mirrors src/api/bot_proxy.gd. `_bot` and `_queued_action` are prefixed
with an underscore by convention only — same as the Godot version's
"not accessible by convention" comment; Python has no true private."""

from __future__ import annotations

from nanobot.core.action_request import ActionRequest
from nanobot.core.nanobot_data import NanoBotData


class BotProxy:
    def __init__(self, bot: NanoBotData):
        self._bot = bot
        self._queued_action: ActionRequest | None = None
        self.id = 0
        self.type = ""
        self.position = (0, 0)
        self.hp = 0
        self.max_hp = 0
        self.azn = 0
        self.is_alive = True
        self.is_moving = False
        self.has_path = False
        self._sync()

    def _sync(self) -> None:
        b = self._bot
        self.id = b.id
        self.type = b.type
        self.position = b.position
        self.hp = b.hp
        self.max_hp = b.max_hp
        self.azn = b.azn_carried
        self.is_alive = b.is_alive
        self.is_moving = b.turns_until_move > 0
        self.has_path = len(b.path_remaining) > 0

    # --- action queue: calling more than one method per turn, last call wins ---

    def move_to(self, target: tuple[int, int]) -> None:
        self._queued_action = ActionRequest.move(target)

    def collect_from(self, source_position: tuple[int, int]) -> None:
        self._queued_action = ActionRequest.collect(source_position)

    def transfer_to(self, target_position: tuple[int, int]) -> None:
        self._queued_action = ActionRequest.transfer(target_position)

    def defend(self, enemy_position: tuple[int, int]) -> None:
        self._queued_action = ActionRequest.defend(enemy_position)

    def build(self, bot_type: str, at_position: tuple[int, int]) -> None:
        self._queued_action = ActionRequest.build(bot_type, at_position)

    def open_ip(self) -> None:
        self._queued_action = ActionRequest.open_ip()

    def stop(self) -> None:
        self._queued_action = ActionRequest.stop()

    def self_destruct(self) -> None:
        self._queued_action = ActionRequest.self_destruct()

    def flush_action(self) -> ActionRequest | None:
        a = self._queued_action
        self._queued_action = None
        return a
