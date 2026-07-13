"""Demonstrates NanoIPCreator (30 AZN) and open_ip(): once built, send it
to a second, far-off Habitas Point and call open_ip() there to register
a brand new injection point — transfer_to() banks AZN whenever a bot is
standing inside *any* injection zone belonging to its owner, not just
the one the NanoAI originally spawned in (simulation_core.py's
_is_at_injection_point checks the whole list). A collector working that
side of the map can bank AZN locally instead of walking all the way back
to the original spawn corner.

NanoIPCreator auto-destructs after 500 turns (data/bot_types.json), but
the injection point it registers is permanent — it's a one-time deploy,
not something that needs to be kept alive.
"""

from __future__ import annotations

import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy
from nanobot.api.reactive_defense import ReactiveDefenseMixin

BUILD_COLLECTOR_COST = 20
BUILD_NEEDLE_COST = 40
BUILD_IP_CREATOR_COST = 30


class ExampleIpCreator(ReactiveDefenseMixin, NanoStrategy):
    def __init__(self) -> None:
        self._second_collector_spawned = False
        self._new_injection_pos: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collector = self._find_bot(my_bots, "NanoCollector")
        needle = self._find_bot(my_bots, "NanoNeedle")
        ip_creator = self._find_bot(my_bots, "NanoIPCreator")
        collectors = [b for b in my_bots if b.type == "NanoCollector" and b.is_alive]

        if nano_ai is None:
            return

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI: collector + needle economy first, then a NanoIPCreator
        # sent toward the *second*-nearest Habitas Point to open a forward
        # bank there. ---

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
        elif ip_creator is None and map_info.azn_bank >= BUILD_IP_CREATOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoIPCreator", adj)
        elif not self._second_collector_spawned and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoCollector", adj)
                self._second_collector_spawned = True
        elif needle is not None:
            # Economy is built out: hand the NanoAI to reactive defense
            # (watchtower explorer, reactive wall, garrison) so a raider
            # can't quietly dismantle the needle. See
            # nanobot/api/reactive_defense.py.
            self.run_defense_ai(map_info, nano_ai, needle, my_bots)
        else:
            nano_ai.stop()

        if needle is not None:
            self.park_watchtower(map_info, my_bots, needle)

        # --- NanoIPCreator: walk to the second-nearest Habitas Point
        # (decided once) and register a new injection point there. ---

        if ip_creator is not None:
            far_hp = self._second_nearest_hp(map_info, needle.position if needle else nano_ai.position)
            if far_hp is not None:
                if ip_creator.position == far_hp.position:
                    ip_creator.open_ip()
                    self._new_injection_pos = far_hp.position
                elif not ip_creator.has_path:
                    ip_creator.move_to(far_hp.position)

        if not collectors:
            return

        # --- Collectors: the first keeps running the usual collect ->
        # deliver-to-needle loop (this is what actually scores). The
        # *second* one (once it exists) is the actual demonstration: it
        # banks AZN at the new injection point — refilling the team's
        # build budget — instead of trekking back to wherever the needle
        # physically is, every time it has something to drop off. Banking
        # doesn't score by itself (only AZN inside a needle does — see
        # simulation_core.py's _update_scores), it just means a far-side
        # collector doesn't waste its time walking the long way home to
        # be useful for builds.
        for i, c in enumerate(collectors):
            if self.shoot_back(map_info, c):
                continue  # a raider is in range — fire instead of hauling AZN
            nearest_azn = self._nearest_azn(map_info, c.position)
            if i == 1 and self._new_injection_pos is not None:
                deliver_target = self._new_injection_pos
            elif needle is not None:
                deliver_target = needle.position
            else:
                deliver_target = None

            if deliver_target is not None and c.azn > 0 and (nearest_azn is None or c.azn >= 10):
                if c.position == deliver_target:
                    c.transfer_to(deliver_target)
                else:
                    c.move_to(deliver_target)
            elif nearest_azn is not None:
                if c.position == nearest_azn.position:
                    c.collect_from(nearest_azn.position)
                else:
                    c.move_to(nearest_azn.position)

    @staticmethod
    def _second_nearest_hp(map_info: MapInfo, from_pos: tuple[int, int]) -> HabitasPointInfo | None:
        by_dist = sorted(
            map_info.habitas_points,
            key=lambda hp: abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1]),
        )
        return by_dist[1] if len(by_dist) > 1 else (by_dist[0] if by_dist else None)

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
