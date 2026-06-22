"""Demonstrates NanoBlocker (20 AZN, +6 turns/cell traversal penalty for
enemies) and NanoWall (25 AZN, fully blocks enemy movement, auto-
destructs after 50 turns): once a Habitas Point is claimed, build both
on the cell between the needle and the map's center — the most likely
direction an opponent approaches from on a map with corner spawns — to
slow or stop a raid before it reaches the needle.

Both only affect *enemy* movement (a friendly bot walks through either
one for free — see simulation_core.py's _find_enemy_wall/_find_enemy_blocker,
which explicitly check owner_id), so placing them doesn't get in your own
collector's way.
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
BUILD_BLOCKER_COST = 20
BUILD_WALL_COST = 25


class ExampleDefense(NanoStrategy):
    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collector = self._find_bot(my_bots, "NanoCollector")
        needle = self._find_bot(my_bots, "NanoNeedle")
        blocker = self._find_bot(my_bots, "NanoBlocker")
        wall = self._find_bot(my_bots, "NanoWall")

        if nano_ai is None:
            return

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI: the usual collector + needle economy first, then
        # spend the rest of the bank fortifying the approach. ---

        if collector is None and map_info.azn_bank >= BUILD_COLLECTOR_COST:
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
        elif needle is not None:
            choke = self._chokepoint(needle.position, map_info)
            if choke != (-1, -1):
                if blocker is None and map_info.azn_bank >= BUILD_BLOCKER_COST \
                        and self._manhattan(nano_ai.position, choke) == 1:
                    nano_ai.build("NanoBlocker", choke)
                elif wall is None and map_info.azn_bank >= BUILD_WALL_COST \
                        and self._manhattan(nano_ai.position, choke) == 1:
                    nano_ai.build("NanoWall", choke)
                elif nano_ai.position != needle.position and self._manhattan(nano_ai.position, choke) != 1:
                    stand = self._approach_pos(choke, nano_ai.position, map_info)
                    if nano_ai.position != stand:
                        nano_ai.move_to(stand)
                    else:
                        nano_ai.stop()
                else:
                    nano_ai.stop()
            else:
                nano_ai.stop()
        else:
            nano_ai.stop()

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
    def _chokepoint(needle_pos: tuple[int, int], map_info: MapInfo) -> tuple[int, int]:
        """The cell adjacent to the needle that's closest to the map's
        center — the most likely direction a corner-spawned opponent
        approaches from."""
        center = (map_info.size[0] / 2, map_info.size[1] / 2)
        best, best_dist = (-1, -1), math.inf
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            c = (needle_pos[0] + dx, needle_pos[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is None or cell.is_bone:
                continue
            d = (c[0] - center[0]) ** 2 + (c[1] - center[1]) ** 2
            if d < best_dist:
                best_dist, best = d, c
        return best

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
