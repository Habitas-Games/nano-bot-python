"""Starter strategy. Copy this file and edit what_to_do_next() /
choose_injection_point().

The bare minimum that actually scores: walk the NanoAI to the nearest
Habitas Point and plant an empty NanoNeedle on it (5 pts/turn — see the
participant guide's scoring table, §6). No collector, no AZN economy —
see example_strategy_v2.py for the fuller loop that fills the needle
with AZN for a much higher score. Build your own strategy from here by
adding bots and logic, not by deleting the one thing this one does.
"""

from __future__ import annotations

import math

from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy

BUILD_NEEDLE_COST = 40


class ExampleStrategy(NanoStrategy):
    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        if nano_ai is None:
            return

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)
        if target_hp is None:
            nano_ai.stop()
            return

        if self._manhattan(nano_ai.position, target_hp.position) == 1 \
                and map_info.azn_bank >= BUILD_NEEDLE_COST:
            nano_ai.build("NanoNeedle", target_hp.position)
            return

        stand_pos = self._approach_pos(target_hp.position, nano_ai.position, map_info)
        if nano_ai.position != stand_pos:
            nano_ai.move_to(stand_pos)
        else:
            nano_ai.stop()

    @staticmethod
    def _find_bot(bots: list[BotProxy], type_name: str) -> BotProxy | None:
        for bot in bots:
            if bot.type == type_name and bot.is_alive:
                return bot
        return None

    @staticmethod
    def _nearest_unoccupied_hp(map_info: MapInfo, from_pos: tuple[int, int]) -> HabitasPointInfo | None:
        best, best_dist = None, math.inf
        for hp in map_info.habitas_points:
            if hp.owner_id != -1:
                continue
            d = abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1])
            if d < best_dist:
                best_dist, best = d, hp
        return best

    @classmethod
    def _approach_pos(cls, target: tuple[int, int], from_pos: tuple[int, int],
                       map_info: MapInfo) -> tuple[int, int]:
        best, best_dist = from_pos, math.inf
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            c = (target[0] + dx, target[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is None or cell.is_bone:
                continue
            d = cls._manhattan(c, from_pos)
            if d < best_dist:
                best_dist, best = d, c
        return best

    @staticmethod
    def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
