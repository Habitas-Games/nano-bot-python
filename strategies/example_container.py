"""Demonstrates NanoContainer (25 AZN, 60 capacity): a two-stage relay
instead of one collector ferrying AZN all the way from a node to the
needle and back on every trip. The container sits roughly halfway
between the AZN node cluster and the needle; the collector's round trip
shrinks to node <-> container, and the container periodically walks its
accumulated stash the rest of the way to the needle. Worthwhile once the
node-to-needle distance is large enough that halving the collector's
round trip matters more than the 25 AZN it costs to build the relay.

transfer_to() works on any bot with storage capacity, not just
NanoNeedle — collector -> container and container -> needle both use the
exact same call.
"""

from __future__ import annotations

import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy

BUILD_COLLECTOR_COST = 20
BUILD_CONTAINER_COST = 25
BUILD_NEEDLE_COST = 40
CONTAINER_HANDOFF_THRESHOLD = 20  # don't bother walking to the needle for a trivial amount


class ExampleContainer(NanoStrategy):
    def __init__(self) -> None:
        self._container_home: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collector = self._find_bot(my_bots, "NanoCollector")
        container = self._find_bot(my_bots, "NanoContainer")
        needle = self._find_bot(my_bots, "NanoNeedle")

        if nano_ai is None:
            return

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI: collector, then a container positioned between the
        # nearest AZN node and the chosen Habitas Point, then the needle. ---

        if collector is None and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoCollector", adj)
        elif container is None and map_info.azn_bank >= BUILD_CONTAINER_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoContainer", adj)
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

        # --- NanoContainer: shuttles between its depot position and the
        # needle. Holds at the depot accumulating AZN from the collector;
        # once it's carrying a worthwhile amount (or nodes are tapped
        # out), it walks to the needle, drops everything off, and heads
        # back to keep collecting — a repeating relay, not a one-shot
        # delivery. ---

        if container is not None and needle is not None:
            if self._container_home is None:
                self._container_home = container.position

            if container.position == needle.position:
                if container.azn > 0:
                    container.transfer_to(needle.position)
                else:
                    container.move_to(self._container_home)
            elif container.azn >= CONTAINER_HANDOFF_THRESHOLD or self._all_azn_nodes_depleted(map_info):
                container.move_to(needle.position)
            elif container.position != self._container_home and not container.has_path:
                container.move_to(self._container_home)

        # --- NanoCollector: shuttle node -> container only (a much
        # shorter round trip than node -> needle once a container exists
        # roughly halfway). Falls back to delivering straight to the
        # needle if no container has been built yet. ---

        if collector is None:
            return

        nearest_azn = self._nearest_azn(map_info, collector.position)
        relay_point = container if container is not None else needle

        if relay_point is not None and collector.azn > 0 and (nearest_azn is None or collector.azn >= 10):
            if collector.position == relay_point.position:
                collector.transfer_to(relay_point.position)
            else:
                collector.move_to(relay_point.position)
        elif nearest_azn is not None:
            if collector.position == nearest_azn.position:
                collector.collect_from(nearest_azn.position)
            else:
                collector.move_to(nearest_azn.position)

    @staticmethod
    def _all_azn_nodes_depleted(map_info: MapInfo) -> bool:
        return all(node.quantity == 0 for node in map_info.azn_nodes)

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
