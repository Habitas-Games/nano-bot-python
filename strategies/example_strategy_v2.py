"""Gameplay loop:
  1. Build a NanoCollector immediately (bank = 150, cost = 20).
  2. Move NanoAI to a cell adjacent to the nearest Habitas Point.
  3. Build NanoNeedle directly ON the Habitas Point (NanoAI is 1 cell away).
  4. Collector collects AZN and delivers it to the NanoNeedle.
"""

from __future__ import annotations

import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy

BUILD_COLLECTOR_COST = 20
BUILD_NEEDLE_COST = 40


class ExampleStrategyV2(NanoStrategy):
    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collector = self._find_bot(my_bots, "NanoCollector")
        needle = self._find_bot(my_bots, "NanoNeedle")

        if nano_ai is None:
            return

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI ---

        if collector is None and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoCollector", adj)
            elif target_hp is not None and nano_ai.position != target_hp.position:
                # Boxed in: every immediate neighbor is Bone. Confirmed via
                # execution on vascular_network.json (shipped until v0.0.16), whose player-0
                # spawn corner (0, 0) has both cardinal neighbors blocked —
                # without this, NanoAI sat frozen at spawn for the entire
                # match, building nothing, scoring 0 every time. Move
                # toward the target point instead; _adjacent_free will
                # find an opening once it's somewhere less boxed-in.
                nano_ai.move_to(target_hp.position)

        elif needle is None and target_hp is not None:
            stand_pos = self._approach_pos(target_hp.position, nano_ai.position, map_info)
            dist_to_hp = self._manhattan(nano_ai.position, target_hp.position)

            if dist_to_hp == 1 and map_info.azn_bank >= BUILD_NEEDLE_COST:
                nano_ai.build("NanoNeedle", target_hp.position)
            elif nano_ai.position != stand_pos:
                nano_ai.move_to(stand_pos)
            else:
                nano_ai.stop()

        else:
            nano_ai.stop()

        # --- NanoCollector ---

        if collector is None:
            return

        nearest_azn = self._nearest_azn(map_info, collector.position)

        if needle is not None and collector.azn > 0 and (nearest_azn is None or collector.azn >= 10):
            if collector.position == needle.position:
                collector.transfer_to(needle.position)
            else:
                collector.move_to(needle.position)
        elif nearest_azn is not None:
            if collector.position == nearest_azn.position:
                collector.collect_from(nearest_azn.position)
            else:
                collector.move_to(nearest_azn.position)

    @staticmethod
    def _find_bot(bots: list[BotProxy], type_name: str) -> BotProxy | None:
        for bot in bots:
            if bot.type == type_name and bot.is_alive:
                return bot
        return None

    @staticmethod
    def _nearest_unoccupied_hp(map_info: MapInfo, from_pos: tuple[int, int]) -> HabitasPointInfo | None:
        # Distance from NanoAI's own actual position, not a hardcoded
        # (0, 0) — the engine assigns each player's real spawn corner
        # from its own injection zone, not literally (0, 0); confirmed
        # via execution this differs when run as player 1 vs player 0.
        best = None
        best_dist = math.inf
        for hp in map_info.habitas_points:
            if hp.owner_id != -1:
                continue
            d = abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1])
            if d < best_dist:
                best_dist = d
                best = hp
        return best

    @staticmethod
    def _nearest_azn(map_info: MapInfo, from_pos: tuple[int, int]) -> AZNNodeInfo | None:
        best = None
        best_dist = math.inf
        for node in map_info.azn_nodes:
            if node.quantity == 0:
                continue
            d = abs(node.position[0] - from_pos[0]) + abs(node.position[1] - from_pos[1])
            if d < best_dist:
                best_dist = d
                best = node
        return best

    @classmethod
    def _approach_pos(cls, target: tuple[int, int], from_pos: tuple[int, int],
                       map_info: MapInfo) -> tuple[int, int]:
        best = from_pos
        best_dist = math.inf
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            c = (target[0] + dx, target[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is None or cell.is_bone:
                continue
            d = cls._manhattan(c, from_pos)
            if d < best_dist:
                best_dist = d
                best = c
        return best

    @staticmethod
    def _adjacent_free(pos: tuple[int, int], map_info: MapInfo) -> tuple[int, int]:
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            c = (pos[0] + dx, pos[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is not None and not cell.is_bone:
                return c
        return (-1, -1)

    @staticmethod
    def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
