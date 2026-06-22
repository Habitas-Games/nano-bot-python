"""Demonstrates NanoExplorer (15 AZN): density_immune means it pays the
flat minimum movement cost through every tissue density instead of the
usual 2/3/4 turns/cell — it reaches a far corner of the map noticeably
faster than any other bot type.

NanoExplorer can't collect, carry, transfer, build, or attack (capacity,
transfer, and max_damage are all 0 in data/bot_types.json) — its only
real job is getting somewhere fast. This strategy runs the same
collect-and-claim economy as example_strategy_v2 for actual scoring, and
sends an Explorer racing to the single farthest Habitas Point purely to
show the speed difference: watch the replay viewer and compare how
quickly it crosses high-density (purple) tissue against how slowly the
NanoAI/NanoCollector do over the same ground.
"""

from __future__ import annotations

import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy

BUILD_EXPLORER_COST = 15
BUILD_COLLECTOR_COST = 20
BUILD_NEEDLE_COST = 40


class ExampleExplorer(NanoStrategy):
    def __init__(self) -> None:
        # Computed once, the first turn the explorer exists, and never
        # recomputed after — recomputing "farthest point from current
        # position" *after* it arrives picks a new farthest point back
        # near the start, sending it oscillating back and forth forever
        # instead of parking. Confirmed this was a real bug by actually
        # running a match and checking the explorer's final position
        # (mid-map, far from either end) before fixing it.
        self._explorer_target: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        explorer = self._find_bot(my_bots, "NanoExplorer")
        collector = self._find_bot(my_bots, "NanoCollector")
        needle = self._find_bot(my_bots, "NanoNeedle")

        if nano_ai is None:
            return

        # --- NanoAI: build order is explorer first (cheapest, and the
        # earlier it leaves the more of the map it covers), then the
        # usual collector + needle economy. ---

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        if explorer is None and map_info.azn_bank >= BUILD_EXPLORER_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoExplorer", adj)
        elif collector is None and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoCollector", adj)
        elif needle is None and target_hp is not None:
            stand_pos = self._approach_pos(target_hp.position, nano_ai.position, map_info)
            if self._manhattan(nano_ai.position, target_hp.position) == 1 \
                    and map_info.azn_bank >= BUILD_NEEDLE_COST:
                nano_ai.build("NanoNeedle", target_hp.position)
            elif nano_ai.position != stand_pos:
                nano_ai.move_to(stand_pos)
            else:
                nano_ai.stop()
        else:
            nano_ai.stop()

        # --- NanoExplorer: race to the single farthest Habitas Point
        # (decided once, from its spawn position) and park there. It
        # can't build or collect once it arrives — this is purely to
        # demonstrate density_immune's speed advantage. ---

        if explorer is not None:
            if self._explorer_target is None:
                farthest_hp = self._farthest_hp(map_info, explorer.position)
                if farthest_hp is not None:
                    self._explorer_target = farthest_hp.position
            if self._explorer_target is not None and explorer.position != self._explorer_target \
                    and not explorer.has_path:
                explorer.move_to(self._explorer_target)

        # --- NanoCollector: same collect -> deliver loop as example_strategy_v2. ---

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
        # Distance from the NanoAI's own actual position, not a hardcoded
        # (0, 0) — see example_combat.py's identical fix for why: each
        # player's real spawn corner depends on its own injection zone,
        # confirmed via execution to differ when run as player 1 instead
        # of player 0.
        best, best_dist = None, math.inf
        for hp in map_info.habitas_points:
            if hp.owner_id != -1:
                continue
            d = abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1])
            if d < best_dist:
                best_dist, best = d, hp
        return best

    @staticmethod
    def _farthest_hp(map_info: MapInfo, from_pos: tuple[int, int]) -> HabitasPointInfo | None:
        best, best_dist = None, -1.0
        for hp in map_info.habitas_points:
            d = abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1])
            if d > best_dist:
                best_dist, best = d, hp
        return best

    @staticmethod
    def _nearest_azn(map_info: MapInfo, from_pos: tuple[int, int]) -> AZNNodeInfo | None:
        best, best_dist = None, math.inf
        for node in map_info.azn_nodes:
            if node.quantity == 0:
                continue
            d = abs(node.position[0] - from_pos[0]) + abs(node.position[1] - from_pos[1])
            if d < best_dist:
                best_dist, best = d, node
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
