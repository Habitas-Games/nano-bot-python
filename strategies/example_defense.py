"""Demonstrates real defense under fog of war + the line-of-sight
combat rule (attacks are blocked by Bone and alive NanoWalls — see
simulation_core.py's _line_blocked).

Standing fortifications don't pay: a wall lasts 50 turns and costs 25,
so keeping even a 3-cell arc up forever costs ~1.5 AZN/turn against a
collector economy that nets a fraction of that. What does pay is
*reactive* defense:

  1. A NanoExplorer (scan 30) parks on the needle as a watchtower —
     without it the defender is blind: an attacker shoots from range 12
     while everything else here sees barely past its own cell.
  2. The NanoAI garrisons the needle. The moment the watchtower spots
     an armed enemy closing in, the AI drops a NanoWall on the exact
     needle-side cell of the firing line. Builds resolve before attacks
     in the turn order, so the wall goes up before the shot lands, and
     every shot after that logs "attack_blocked".
  3. A one-off NanoBlocker on the center-facing cell slows anyone who
     tries to walk around the wall instead.

Wall spend only happens during an actual raid, funded by the collector
banking its surplus once the needle reaches a 40 pts/turn score floor.
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
BUILD_BLOCKER_COST = 20
BUILD_WALL_COST = 25


NEEDLE_SCORE_FLOOR = 10  # secure a 40 pts/turn floor before saving for walls
WAR_CHEST = 60           # bank this much for reactive walls, then go back to scoring
BUILD_EXPLORER_COST = 15
THREAT_RADIUS = 16  # react when an armed enemy gets this close to the needle


class ExampleDefense(ReactiveDefenseMixin, NanoStrategy):
    def __init__(self) -> None:
        self._spawn_pos: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collector = self._find_bot(my_bots, "NanoCollector")
        needle = self._find_bot(my_bots, "NanoNeedle")
        blocker = self._find_bot(my_bots, "NanoBlocker")
        watchtower = self._find_bot(my_bots, "NanoExplorer")
        walls = [b for b in my_bots if b.type == "NanoWall" and b.is_alive]

        if nano_ai is None:
            return
        if self._spawn_pos is None:
            self._spawn_pos = nano_ai.position

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI build order: collector -> needle -> watchtower
        # explorer -> blocker. After that it garrisons the needle and
        # only spends when a raid actually comes. ---

        threat = self._nearest_threat(map_info, needle.position) if needle is not None else None

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
        elif needle is not None and threat is not None and map_info.azn_bank >= BUILD_WALL_COST:
            # Raid response: wall the needle-side cell of the firing line.
            shield_cell = self._intercept_cell(needle.position, threat["position"], map_info)
            if shield_cell is not None and not any(w.position == shield_cell for w in walls):
                self._go_build(nano_ai, map_info, shield_cell, "NanoWall")
            else:
                nano_ai.stop()
        elif needle is not None and watchtower is None and map_info.azn_bank >= BUILD_EXPLORER_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoExplorer", adj)
        elif needle is not None and blocker is None and map_info.azn_bank >= BUILD_BLOCKER_COST:
            shield = self._shield_cells(needle.position, map_info)
            if shield:
                self._go_build(nano_ai, map_info, shield[0], "NanoBlocker")
            else:
                nano_ai.stop()
        elif needle is not None and nano_ai.position != needle.position:
            nano_ai.move_to(needle.position)  # garrison: stand on the needle, ready to build
        else:
            nano_ai.stop()

        # --- Watchtower: park on the needle. Its scan 30 is the alarm
        # system; without it the first sign of a raid is the needle
        # losing HP to an invisible attacker 12 cells away. ---
        if watchtower is not None and needle is not None \
                and watchtower.position != needle.position and not watchtower.has_path:
            watchtower.move_to(needle.position)

        # --- NanoCollector: feed the needle up to its score floor, then
        # switch to banking at the injection zone so the wall upkeep
        # never runs dry. ---

        if collector is None:
            return

        # Shoot back at a raider in range before doing economy. Without
        # this the watchtower + reactive wall alone can't win the fight
        # (measured: wall-without-shoot loses to example_combat 0/24) —
        # the wall buys time, the return fire drives the raider off.
        if self.shoot_back(map_info, collector):
            return

        # Feed the needle and stay near it — do NOT trek off to bank AZN.
        # The old war-chest banking (deliver surplus to spawn) pulled the
        # collector away from the needle, so it was never positioned to
        # shoot back at a raider, and lost to example_combat 0/24. The
        # reactive walls are funded from the starting 150-AZN bank (which
        # covers several walls before the raid arrives — the same way
        # example_strategy_v2 defends without ever banking). Keeping the
        # collector home to feed and shoot flips the matchup.
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

    def _go_build(self, nano_ai: BotProxy, map_info: MapInfo,
                   cell: tuple[int, int], bot_type: str) -> None:
        if self._manhattan(nano_ai.position, cell) == 1:
            nano_ai.build(bot_type, cell)
            return
        stand = self._approach_pos(cell, nano_ai.position, map_info)
        if nano_ai.position != stand:
            nano_ai.move_to(stand)
        else:
            nano_ai.stop()

    @staticmethod
    def _nearest_threat(map_info: MapInfo, needle_pos: tuple[int, int]) -> dict | None:
        best, best_d = None, THREAT_RADIUS
        for e in map_info.visible_enemies:
            if e["type"] != "NanoCollector":
                continue  # only collectors can shoot
            d = math.hypot(e["position"][0] - needle_pos[0], e["position"][1] - needle_pos[1])
            if d <= best_d:
                best_d, best = d, e
        return best

    @staticmethod
    def _intercept_cell(needle_pos: tuple[int, int], enemy_pos: tuple[int, int],
                         map_info: MapInfo) -> tuple[int, int] | None:
        """The needle's neighbor cell in the enemy's direction — the first
        cell every shot on the needle must cross."""
        sx = (enemy_pos[0] > needle_pos[0]) - (enemy_pos[0] < needle_pos[0])
        sy = (enemy_pos[1] > needle_pos[1]) - (enemy_pos[1] < needle_pos[1])
        c = (needle_pos[0] + sx, needle_pos[1] + sy)
        if c == needle_pos:
            return None
        if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
            return None
        cell = map_info.get_cell(c[0], c[1])
        if cell is None or cell.is_bone:
            return None
        return c

    @staticmethod
    def _shield_cells(needle_pos: tuple[int, int], map_info: MapInfo) -> list[tuple[int, int]]:
        """Three cells on the map-center-facing side of the needle — the
        two center-facing cardinals plus the diagonal between them. Shots
        from the whole center-side quadrant have to cross one of these,
        so keeping walls alive on them blanks that entire approach cone
        (Bone and the map edge cover much of the rest on corner maps)."""
        cx, cy = map_info.size[0] / 2, map_info.size[1] / 2
        sx = 1 if cx >= needle_pos[0] else -1
        sy = 1 if cy >= needle_pos[1] else -1
        candidates = [
            (needle_pos[0] + sx, needle_pos[1]),
            (needle_pos[0], needle_pos[1] + sy),
            (needle_pos[0] + sx, needle_pos[1] + sy),
        ]
        cells = []
        for c in candidates:
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is not None and not cell.is_bone:
                cells.append(c)
        return cells

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
