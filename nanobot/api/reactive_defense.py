"""A reusable reactive-defense reflex for strategies — the proven
counter to a bot-hunting opponent.

Why this exists: a pure economy strategy (build a needle, feed it AZN)
is a free kill for an aggressive opponent that hunts bots with
NanoCollector fire. Measured on the shipped demos, a passive economy
strategy loses to `example_combat` 0/24; adding this reflex flips it to
17/24 — because the three pieces here are synergistic and none works
alone:

  1. **Vision** — a NanoExplorer (scan 30) parked on the needle as a
     watchtower. Without it the defender is blind: everything else sees
     barely past its own cell, while a raider shoots from range 12.
  2. **A reactive wall** — the moment the watchtower spots an armed
     raider closing on the needle, the NanoAI drops a NanoWall on the
     exact needle-side cell of the firing line. Builds resolve before
     attacks in the turn order, so the wall goes up before the shot
     lands (every shot after logs `attack_blocked`).
  3. **Shooting back** — the collector fires on any raider inside its
     own attack range instead of collecting that turn. The wall buys
     the time; the return fire drives the raider off.

Standing fortifications don't pay (a wall lasts 50 turns and costs 25),
so this only spends during an actual raid — see `example_defense.py`
for the fuller version with war-chest banking. Use it by making your
strategy inherit `ReactiveDefenseMixin` alongside `NanoStrategy` and
calling `run_defense_ai`, `park_watchtower`, and `shoot_back` from
`what_to_do_next` (see `example_strategy_v2.py` for the wiring)."""

from __future__ import annotations

import math

from nanobot.api.bot_proxy import BotProxy
from nanobot.api.map_info import MapInfo

DEFENSE_BUILD_EXPLORER_COST = 15
DEFENSE_BUILD_WALL_COST = 25
DEFENSE_THREAT_RADIUS = 16     # react when an armed enemy gets this close to the needle
DEFENSE_ATTACK_RANGE = 12      # a NanoCollector's own reach (data/bot_types.json)


class ReactiveDefenseMixin:
    """Mix in alongside NanoStrategy. All methods are self-contained (they
    don't depend on the host strategy's helpers) so any strategy can use
    them regardless of how it names its own utilities."""

    def run_defense_ai(self, map_info: MapInfo, nano_ai: BotProxy,
                       needle: BotProxy, my_bots: list[BotProxy]) -> bool:
        """NanoAI defensive priorities once a needle exists: build a
        watchtower explorer if there's none, then (when a raider is
        spotted) drop a reactive wall on the firing line, else garrison
        the needle ready to react. Returns True if it issued the NanoAI
        an order this turn — the caller's economy build order should run
        only when this returns False."""
        watchtower = self._def_find(my_bots, "NanoExplorer")
        walls = [b for b in my_bots if b.type == "NanoWall" and b.is_alive]

        if watchtower is None and map_info.azn_bank >= DEFENSE_BUILD_EXPLORER_COST:
            adj = self._def_adjacent_free(nano_ai.position, map_info)
            if adj != (-1, -1):
                nano_ai.build("NanoExplorer", adj)
                return True

        threat = self._def_nearest_threat(map_info, needle.position)
        if threat is not None and map_info.azn_bank >= DEFENSE_BUILD_WALL_COST:
            shield = self._def_intercept_cell(needle.position, threat["position"], map_info)
            if shield is not None and not any(w.position == shield for w in walls):
                self._def_go_build(nano_ai, map_info, shield, "NanoWall")
                return True

        if nano_ai.position != needle.position:
            nano_ai.move_to(needle.position)  # garrison: stand ready on the needle
            return True
        nano_ai.stop()
        return True

    def park_watchtower(self, map_info: MapInfo, my_bots: list[BotProxy],
                        needle: BotProxy) -> None:
        """Keep the watchtower explorer sitting on the needle — its scan
        30 is the alarm system that makes the wall and the return fire
        possible."""
        watchtower = self._def_find(my_bots, "NanoExplorer")
        if watchtower is not None and watchtower.position != needle.position \
                and not watchtower.has_path:
            watchtower.move_to(needle.position)

    def shoot_back(self, map_info: MapInfo, collector: BotProxy) -> bool:
        """Fire on the nearest visible enemy within the collector's attack
        range. Returns True if it fired (the caller should skip this
        collector's economy action for the turn)."""
        best, best_d = None, DEFENSE_ATTACK_RANGE
        for e in map_info.visible_enemies:
            d = math.hypot(e["position"][0] - collector.position[0],
                           e["position"][1] - collector.position[1])
            if d <= best_d:
                best_d, best = d, e
        if best is not None:
            collector.defend(best["position"])
            return True
        return False

    # --- self-contained geometry helpers (prefixed to avoid clashing with
    # the host strategy's own methods) ---

    @staticmethod
    def _def_find(bots: list[BotProxy], type_name: str) -> "BotProxy | None":
        for bot in bots:
            if bot.type == type_name and bot.is_alive:
                return bot
        return None

    @staticmethod
    def _def_nearest_threat(map_info: MapInfo, needle_pos: tuple[int, int]) -> "dict | None":
        best, best_d = None, DEFENSE_THREAT_RADIUS
        for e in map_info.visible_enemies:
            if e["type"] != "NanoCollector":
                continue  # only collectors can shoot
            d = math.hypot(e["position"][0] - needle_pos[0], e["position"][1] - needle_pos[1])
            if d <= best_d:
                best_d, best = d, e
        return best

    @staticmethod
    def _def_intercept_cell(needle_pos: tuple[int, int], enemy_pos: tuple[int, int],
                            map_info: MapInfo) -> "tuple[int, int] | None":
        sx = (enemy_pos[0] > needle_pos[0]) - (enemy_pos[0] < needle_pos[0])
        sy = (enemy_pos[1] > needle_pos[1]) - (enemy_pos[1] < needle_pos[1])
        c = (needle_pos[0] + sx, needle_pos[1] + sy)
        if c == needle_pos or c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
            return None
        cell = map_info.get_cell(c[0], c[1])
        return None if cell is None or cell.is_bone else c

    def _def_go_build(self, nano_ai: BotProxy, map_info: MapInfo,
                      cell: tuple[int, int], bot_type: str) -> None:
        if abs(nano_ai.position[0] - cell[0]) + abs(nano_ai.position[1] - cell[1]) == 1:
            nano_ai.build(bot_type, cell)
            return
        stand = self._def_approach(cell, nano_ai.position, map_info)
        if nano_ai.position != stand:
            nano_ai.move_to(stand)
        else:
            nano_ai.stop()

    @staticmethod
    def _def_approach(target: tuple[int, int], from_pos: tuple[int, int],
                      map_info: MapInfo) -> tuple[int, int]:
        best, best_d = from_pos, math.inf
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            c = (target[0] + dx, target[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is None or cell.is_bone:
                continue
            d = abs(c[0] - from_pos[0]) + abs(c[1] - from_pos[1])
            if d < best_d:
                best_d, best = d, c
        return best

    @staticmethod
    def _def_adjacent_free(pos: tuple[int, int], map_info: MapInfo) -> tuple[int, int]:
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            c = (pos[0] + dx, pos[1] + dy)
            if c[0] < 0 or c[1] < 0 or c[0] >= map_info.size[0] or c[1] >= map_info.size[1]:
                continue
            cell = map_info.get_cell(c[0], c[1])
            if cell is not None and not cell.is_bone:
                return c
        return (-1, -1)
