"""One queued action per bot per turn. Mirrors src/core/action_request.gd."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionType(Enum):
    NONE = "none"
    MOVE = "move"
    COLLECT = "collect"
    TRANSFER = "transfer"
    DEFEND = "defend"
    BUILD = "build"
    OPEN_IP = "open_ip"
    STOP = "stop"
    SELF_DESTRUCT = "self_destruct"


@dataclass
class ActionRequest:
    action_type: ActionType = ActionType.NONE
    target_position: tuple[int, int] = field(default=(-1, -1))
    build_type: str = ""

    @staticmethod
    def move(target: tuple[int, int]) -> "ActionRequest":
        return ActionRequest(ActionType.MOVE, target_position=target)

    @staticmethod
    def collect(source: tuple[int, int]) -> "ActionRequest":
        return ActionRequest(ActionType.COLLECT, target_position=source)

    @staticmethod
    def transfer(dest: tuple[int, int]) -> "ActionRequest":
        return ActionRequest(ActionType.TRANSFER, target_position=dest)

    @staticmethod
    def defend(enemy_pos: tuple[int, int]) -> "ActionRequest":
        return ActionRequest(ActionType.DEFEND, target_position=enemy_pos)

    @staticmethod
    def build(bot_type: str, pos: tuple[int, int]) -> "ActionRequest":
        return ActionRequest(ActionType.BUILD, target_position=pos, build_type=bot_type)

    @staticmethod
    def open_ip() -> "ActionRequest":
        return ActionRequest(ActionType.OPEN_IP)

    @staticmethod
    def stop() -> "ActionRequest":
        return ActionRequest(ActionType.STOP)

    @staticmethod
    def self_destruct() -> "ActionRequest":
        return ActionRequest(ActionType.SELF_DESTRUCT)

    def type_name(self) -> str:
        return self.action_type.value
