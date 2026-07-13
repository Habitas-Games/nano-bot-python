"""The economy powerhouse — the 'greedy economy' corner of the strategy
rock-paper-scissors.

Where example_strategy_v2 fortifies a single needle, this claims and
feeds TWO Habitas Points. Two needles score more than one (double the
20-point base, plus AZN split across both), so a well-fed two-needle
economy OUT-SCORES a single-needle turtle like example_defense — the
edge that stops any one archetype dominating the tournament:

    aggression (combat)  beats  greedy economy (this)
    greedy economy       beats  turtle defense
    turtle defense       beats  aggression

The cost of that scoring is exposure: two needles spread across the map
can't both be defended, so an aggressor that hunts bots
(example_combat) picks this apart. It runs deliberately defense-light —
no walls, no watchtower — because being beatable by aggression is its
role in the cycle, not a flaw. One collector keeps a one-needle reserve
banked (40 AZN) so a needle lost to a raider or a contested AZN node
can be reclaimed instead of leaving it permanently a point down.
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
WANT_NEEDLES = 2
WANT_COLLECTORS = 2
BUILD_RESERVE = 40   # keep this much banked so a lost needle can be rebuilt


class ExampleFullRoster(NanoStrategy):
    def __init__(self) -> None:
        self._spawn_pos: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        if nano_ai is None:
            return
        if self._spawn_pos is None:
            self._spawn_pos = nano_ai.position

        collectors = [b for b in my_bots if b.type == "NanoCollector" and b.is_alive]
        needles = [b for b in my_bots if b.type == "NanoNeedle" and b.is_alive]
        unclaimed = [hp for hp in map_info.habitas_points if hp.owner_id == -1]

        # --- NanoAI build order: collector, needle, collector, needle,
        # then keep two needles standing (reclaim any that fall). ---
        if len(collectors) < 1 and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif len(needles) < 1 and unclaimed:
            self._go_claim(nano_ai, map_info, unclaimed)
        elif len(collectors) < WANT_COLLECTORS and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif len(needles) < WANT_NEEDLES and unclaimed and map_info.azn_bank >= BUILD_NEEDLE_COST:
            self._go_claim(nano_ai, map_info, unclaimed)
        elif needles:
            # Everything's up (or waiting on the reserve to reclaim a lost
            # needle): garrison the nearest needle.
            nearest = min(needles, key=lambda n: self._manhattan(nano_ai.position, n.position))
            if nano_ai.position != nearest.position:
                nano_ai.move_to(nearest.position)
            else:
                nano_ai.stop()
        else:
            nano_ai.stop()

        # --- Collectors: feed the needles. While a needle slot is empty
        # and the reserve isn't saved yet, one collector banks toward the
        # reserve so the NanoAI can afford to rebuild; the rest pour AZN
        # into needles where it scores. ---
        need_reserve = len(needles) < WANT_NEEDLES and map_info.azn_bank < BUILD_RESERVE
        for i, c in enumerate(collectors):
            nearest_azn = self._nearest_azn(map_info, c.position)
            if not needles:
                self._harvest(c, nearest_azn)
                continue
            if need_reserve and i == 0 and c.azn > 0 and self._spawn_pos is not None:
                # Bank at the spawn injection zone to refill the build
                # budget (the engine banks a transfer made inside any of
                # your injection zones — the original spawn is one).
                if c.position == self._spawn_pos:
                    c.transfer_to(self._spawn_pos)
                else:
                    c.move_to(self._spawn_pos)
                continue
            target = needles[i % len(needles)]
            if c.azn > 0 and (nearest_azn is None or c.azn >= 10):
                if c.position == target.position:
                    c.transfer_to(target.position)
                else:
                    c.move_to(target.position)
            else:
                self._harvest(c, nearest_azn)

    # --- helpers ---

    @staticmethod
    def _harvest(collector: BotProxy, node: "AZNNodeInfo | None") -> None:
        if node is None:
            return
        if collector.position == node.position:
            collector.collect_from(node.position)
        else:
            collector.move_to(node.position)

    def _go_claim(self, nano_ai: BotProxy, map_info: MapInfo,
                  unclaimed: list["HabitasPointInfo"]) -> None:
        target = min(unclaimed, key=lambda h: self._manhattan(nano_ai.position, h.position))
        if self._manhattan(nano_ai.position, target.position) == 1 \
                and map_info.azn_bank >= BUILD_NEEDLE_COST:
            nano_ai.build("NanoNeedle", target.position)
            return
        stand = self._approach_pos(target.position, nano_ai.position, map_info)
        if nano_ai.position != stand:
            nano_ai.move_to(stand)
        else:
            nano_ai.stop()

    def _build_adjacent(self, nano_ai: BotProxy, map_info: MapInfo, bot_type: str) -> None:
        adj = self._adjacent_free(nano_ai.position, map_info)
        if adj != (-1, -1):
            nano_ai.build(bot_type, adj)

    @staticmethod
    def _find_bot(bots: list[BotProxy], type_name: str) -> "BotProxy | None":
        for bot in bots:
            if bot.type == type_name and bot.is_alive:
                return bot
        return None

    @staticmethod
    def _nearest_azn(map_info: MapInfo, from_pos: tuple[int, int]) -> "AZNNodeInfo | None":
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
