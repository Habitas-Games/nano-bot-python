"""Demonstrates defend() (attack) under fog of war: NanoCollector is
the only bot type with an attack stat (1-5 damage, range 12 — see
data/bot_types.json), but its scan is 0 — it can barely see past its
own cell. Enemies only appear in map_info.visible_enemies while inside
some friendly bot's scan radius, so a fighter needs a *spotter*: this
strategy pairs its fighting collector with a NanoExplorer (scan 30)
scouting toward the enemy's likely corner. Artillery + forward observer.

Attacks also require line of sight — Bone and alive NanoWalls (anyone's)
block the shot (an "attack_blocked" event is logged). And defend() must
be re-issued with the enemy's current position every turn; bots don't
auto-track.

A collector that's actively fighting doesn't also collect or deliver
that turn (only the last queued action per bot per turn takes effect),
so this strategy only commits a *second* collector to combat once the
first one has the economy loop covered.
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
BUILD_EXPLORER_COST = 15
ATTACK_RANGE = 12


class ExampleCombat(NanoStrategy):
    def __init__(self) -> None:
        self._spawn_pos: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        collectors = [b for b in my_bots if b.type == "NanoCollector" and b.is_alive]
        needle = self._find_bot(my_bots, "NanoNeedle")
        scout = self._find_bot(my_bots, "NanoExplorer")

        if nano_ai is None:
            return
        if self._spawn_pos is None:
            self._spawn_pos = nano_ai.position

        target_hp = self._nearest_unoccupied_hp(map_info, nano_ai.position)

        # --- NanoAI: economy collector, needle, then a second collector
        # whose whole job is fighting. ---

        if len(collectors) == 0 and map_info.azn_bank >= BUILD_COLLECTOR_COST:
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
        elif scout is None and map_info.azn_bank >= BUILD_EXPLORER_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoExplorer", adj)
        elif len(collectors) == 1 and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            adj = self._adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoCollector", adj)
        else:
            nano_ai.stop()

        # --- Scout: sweep between the enemy's likely spawn corner (the
        # mirror of ours) and the map center, lighting up targets for
        # the fighter. Under fog this is what makes combat possible at
        # all: the fighter's own scan is ~0.
        if scout is not None:
            w, h = map_info.size
            mirror = (w - 1 - self._spawn_pos[0], h - 1 - self._spawn_pos[1])
            center = (w // 2, h // 2)
            if not scout.has_path:
                target = mirror if scout.position != mirror else center
                if scout.position == center:
                    target = mirror
                scout.move_to(target)

        if not collectors:
            return

        economy_collector = collectors[0]
        fighter = collectors[1] if len(collectors) > 1 else None

        # --- Economy collector: same collect -> deliver loop as
        # example_strategy_v2. ---

        nearest_azn = self._nearest_azn(map_info, economy_collector.position)
        if needle is not None and economy_collector.azn > 0 \
                and (nearest_azn is None or economy_collector.azn >= 10):
            if economy_collector.position == needle.position:
                economy_collector.transfer_to(needle.position)
            else:
                economy_collector.move_to(needle.position)
        elif nearest_azn is not None:
            if economy_collector.position == nearest_azn.position:
                economy_collector.collect_from(nearest_azn.position)
            else:
                economy_collector.move_to(nearest_azn.position)

        # --- Fighter: chase whichever visible enemy is nearest. Attack
        # whenever already in range; otherwise close the distance. ---

        if fighter is None:
            return

        nearest_enemy = self._nearest_enemy(map_info, fighter.position)
        if nearest_enemy is None:
            # Nothing spotted: shadow the scout so the fighter is already
            # close when a target lights up.
            if scout is not None and self._manhattan(fighter.position, scout.position) > 4:
                fighter.move_to(scout.position)
            else:
                fighter.stop()
            return

        enemy_pos = tuple(nearest_enemy["position"])
        dist = math.hypot(fighter.position[0] - enemy_pos[0], fighter.position[1] - enemy_pos[1])
        if dist <= ATTACK_RANGE:
            fighter.defend(enemy_pos)
        else:
            fighter.move_to(enemy_pos)

    @staticmethod
    def _nearest_enemy(map_info: MapInfo, from_pos: tuple[int, int]) -> dict | None:
        best, best_dist = None, math.inf
        for enemy in map_info.visible_enemies:
            ex, ey = enemy["position"]
            d = math.hypot(ex - from_pos[0], ey - from_pos[1])
            if d < best_dist:
                best_dist, best = d, enemy
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
        # (0, 0) — confirmed via execution that the engine assigns each
        # player's real spawn corner based on its own injection zone, not
        # literally (0, 0): choose_injection_point() requesting (0, 0)
        # only resolves there for whichever player's zone happens to
        # contain it (player 0 on the bundled maps); running the same
        # strategy as player 1 spawns it in a different corner entirely,
        # and measuring "nearest" from the wrong reference point sent it
        # after the *farthest* Habitas Point instead.
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
