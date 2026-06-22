"""The comprehensive demo: all 8 bot types working together as one real
competitive approach, not 5 separate single-mechanic showcases. Combines
every other example_*.py in this directory into one build order:

1. Collector + Needle on the nearest Habitas Point (the core economic
   loop, same as example_strategy_v2).
2. NanoBlocker + NanoWall on that point's chokepoint, rebuilding the wall
   whenever it auto-destructs (example_defense).
3. A NanoExplorer sent racing toward a second Habitas Point — density
   immunity gets it there fast, and the NanoAI doesn't commit to the
   long trek of claiming that second point itself until the Explorer
   has actually confirmed it's reachable (example_explorer).
4. A second Collector + Needle on that second point once the NanoAI
   arrives (more claimed points beats one fully-loaded point — see
   the participant guide's tips section).
5. A NanoIPCreator opens a forward injection point near the second
   point, so its collector banks locally for builds instead of
   trekking back to spawn (example_ip_creator).
6. A NanoContainer relay for the second point if its nearest AZN node
   turns out to be far from the needle (example_container).
7. Once both points are funded, a third Collector becomes a dedicated
   fighter, hunting visible enemies with defend() (example_combat).
"""

from __future__ import annotations

import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy

COST = {
    "NanoExplorer": 15, "NanoCollector": 20, "NanoContainer": 25,
    "NanoNeedle": 40, "NanoIPCreator": 30, "NanoBlocker": 20, "NanoWall": 25,
}
CONTAINER_RELAY_DISTANCE_THRESHOLD = 12  # only worth building if the node is this far from the needle
CONTAINER_HANDOFF_THRESHOLD = 20
ATTACK_RANGE = 12
NEEDLE1_FUNDING_CAP = 30  # stop over-funding needle 1; bank the rest to fund expansion instead


class ExampleFullRoster(NanoStrategy):
    def __init__(self) -> None:
        self._point1: tuple[int, int] | None = None
        self._point2: tuple[int, int] | None = None
        self._explorer_target: tuple[int, int] | None = None
        self._new_injection_pos: tuple[int, int] | None = None
        self._container_home: tuple[int, int] | None = None
        self._wall_builds = 0
        self._spawn_pos: tuple[int, int] | None = None

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find_bot(my_bots, "NanoAI")
        if nano_ai is None:
            return

        collectors = [b for b in my_bots if b.type == "NanoCollector" and b.is_alive]
        needles = [b for b in my_bots if b.type == "NanoNeedle" and b.is_alive]
        explorer = self._find_bot(my_bots, "NanoExplorer")
        blocker = self._find_bot(my_bots, "NanoBlocker")
        wall = self._find_bot(my_bots, "NanoWall")
        ip_creator = self._find_bot(my_bots, "NanoIPCreator")
        container = self._find_bot(my_bots, "NanoContainer")

        if self._spawn_pos is None:
            # Captured once, on the first turn, before NanoAI moves —
            # the actual injection zone position, not a hardcoded (0, 0).
            # Confirmed via execution that the engine assigns each
            # player's real spawn corner from its own injection zone, not
            # literally (0, 0) — running as player 1 instead of player 0
            # spawns in a different corner entirely, and every "nearest"/
            # "bank near spawn" calculation here needs the real one.
            self._spawn_pos = nano_ai.position
        if self._point1 is None:
            hp = self._nearest_unoccupied_hp(map_info, self._spawn_pos)
            self._point1 = hp.position if hp else None

        needle1 = self._needle_at(needles, self._point1)
        needle2 = self._needle_at(needles, self._point2) if self._point2 else None

        self._run_nano_ai(map_info, nano_ai, collectors, needle1, needle2,
                           explorer, blocker, wall, ip_creator, container)
        self._run_explorer(map_info, explorer)
        self._run_ip_creator(map_info, ip_creator, needle2)
        self._run_collectors(map_info, collectors, needle1, needle2, container)
        self._run_container(container, needle2)

    # --- NanoAI: one long priority chain, one action per turn ---

    def _run_nano_ai(self, map_info, nano_ai, collectors, needle1, needle2,
                      explorer, blocker, wall, ip_creator, container) -> None:
        bank = map_info.azn_bank
        collector1 = collectors[0] if collectors else None

        if collector1 is None and bank >= COST["NanoCollector"]:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif needle1 is None and self._point1 is not None:
            self._travel_and_build(nano_ai, map_info, self._point1, "NanoNeedle")
        elif blocker is None and bank >= COST["NanoBlocker"] and needle1 is not None:
            choke = self._chokepoint(needle1.position, map_info)
            if choke != (-1, -1):
                self._travel_and_build(nano_ai, map_info, choke, "NanoBlocker")
        elif wall is None and self._wall_builds < 2 and bank >= COST["NanoWall"] and needle1 is not None:
            # Capped, not rebuilt forever: NanoWall auto-destructs every
            # ~50 turns, and at 25 AZN a rebuild, maintaining it
            # indefinitely (confirmed via execution) drains AZN faster
            # than the rest of the economy can replace it — every other
            # build (second point, IP creator, container, fighter)
            # starved permanently with the wall left unbounded. One
            # rebuild is enough to demonstrate the mechanic; the
            # NanoBlocker (no auto-destruct, no upkeep) keeps the
            # chokepoint at least partially defended for free afterward.
            choke = self._chokepoint(needle1.position, map_info)
            if choke != (-1, -1):
                if self._manhattan(nano_ai.position, choke) == 1 and bank >= COST["NanoWall"]:
                    self._wall_builds += 1
                self._travel_and_build(nano_ai, map_info, choke, "NanoWall")
        elif explorer is None and bank >= COST["NanoExplorer"]:
            self._build_adjacent(nano_ai, map_info, "NanoExplorer")
        elif needle2 is None and self._explorer_arrived(explorer):
            self._travel_and_build(nano_ai, map_info, self._point2, "NanoNeedle")
        elif needle2 is not None and len(collectors) < 2 and bank >= COST["NanoCollector"]:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif needle2 is not None and ip_creator is None and bank >= COST["NanoIPCreator"]:
            self._build_adjacent(nano_ai, map_info, "NanoIPCreator")
        elif needle2 is not None and container is None and bank >= COST["NanoContainer"] \
                and self._container_worth_building(map_info, needle2.position):
            self._build_adjacent(nano_ai, map_info, "NanoContainer")
        elif needle1 is not None and needle2 is not None and len(collectors) < 3 \
                and bank >= COST["NanoCollector"]:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        else:
            nano_ai.stop()

    def _container_worth_building(self, map_info: MapInfo, needle_pos: tuple[int, int]) -> bool:
        nearest = self._nearest_azn(map_info, needle_pos)
        if nearest is None:
            return False
        return self._manhattan(nearest.position, needle_pos) >= CONTAINER_RELAY_DISTANCE_THRESHOLD

    def _build_adjacent(self, nano_ai: BotProxy, map_info: MapInfo, bot_type: str) -> None:
        adj = self._adjacent_free(nano_ai.position, map_info)
        if adj != (-1, -1):
            nano_ai.build(bot_type, adj)

    def _travel_and_build(self, nano_ai: BotProxy, map_info: MapInfo,
                           target: tuple[int, int], bot_type: str) -> None:
        if self._manhattan(nano_ai.position, target) == 1 and map_info.azn_bank >= COST[bot_type]:
            nano_ai.build(bot_type, target)
            return
        stand_pos = self._approach_pos(target, nano_ai.position, map_info)
        if nano_ai.position != stand_pos:
            nano_ai.move_to(stand_pos)
        else:
            nano_ai.stop()

    def _explorer_arrived(self, explorer: BotProxy | None) -> bool:
        return explorer is not None and self._explorer_target is not None \
            and explorer.position == self._explorer_target

    # --- NanoExplorer: race to a second Habitas Point, decided once ---

    def _run_explorer(self, map_info: MapInfo, explorer: BotProxy | None) -> None:
        if explorer is None:
            return
        if self._point2 is None:
            hp = self._second_point(map_info)
            if hp is not None:
                self._point2 = hp.position
                self._explorer_target = hp.position
        if self._explorer_target is not None and explorer.position != self._explorer_target \
                and not explorer.has_path:
            explorer.move_to(self._explorer_target)

    # --- NanoIPCreator: open a forward bank near the second point ---

    def _run_ip_creator(self, map_info: MapInfo, ip_creator: BotProxy | None, needle2: BotProxy | None) -> None:
        if ip_creator is None or self._point2 is None:
            return
        if ip_creator.position == self._point2:
            ip_creator.open_ip()
            self._new_injection_pos = self._point2
        elif not ip_creator.has_path:
            ip_creator.move_to(self._point2)

    # --- NanoContainer: shuttle relay for the second point ---

    def _run_container(self, container: BotProxy | None, needle2: BotProxy | None) -> None:
        if container is None or needle2 is None:
            return
        if self._container_home is None:
            self._container_home = container.position
        if container.position == needle2.position:
            if container.azn > 0:
                container.transfer_to(needle2.position)
            else:
                container.move_to(self._container_home)
        elif container.azn >= CONTAINER_HANDOFF_THRESHOLD:
            container.move_to(needle2.position)
        elif container.position != self._container_home and not container.has_path:
            container.move_to(self._container_home)

    # --- Collectors: first two run the economy, a third (once both
    # points are funded) becomes a dedicated fighter. ---

    def _run_collectors(self, map_info: MapInfo, collectors: list[BotProxy],
                         needle1: BotProxy | None, needle2: BotProxy | None,
                         container: BotProxy | None) -> None:
        if not collectors:
            return

        economy = collectors[:2]
        fighter = collectors[2] if len(collectors) > 2 else None

        for i, c in enumerate(economy):
            needle = needle1 if i == 0 else (needle2 if needle2 is not None else needle1)
            if i == 0 and needle1 is not None and needle1.azn >= NEEDLE1_FUNDING_CAP:
                # Once the first needle has a respectable baseline score
                # (20 + 2*30 = 80 pts), stop over-funding it and bank the
                # rest near spawn instead — confirmed via execution that
                # without this, every further build (second point, IP
                # creator, container, fighter) was permanently starved:
                # transfer_to() only ever delivers to a needle or banks,
                # never both, so a collector that always targets the
                # needle never refills the team's build budget, which
                # otherwise never grows past whatever's left of the
                # starting 150 after the first few builds.
                relay_target = self._spawn_pos
            elif i == 1 and container is not None:
                relay_target = container.position
            elif i == 1 and self._new_injection_pos is not None and needle is not None:
                relay_target = min([needle.position, self._new_injection_pos],
                                    key=lambda p: self._manhattan(c.position, p))
            elif needle is not None:
                relay_target = needle.position
            else:
                relay_target = None

            nearest_azn = self._nearest_azn(map_info, c.position)
            # Finishing a delivery already in progress always takes
            # priority over heading back out to collect more — confirmed
            # via execution that checking the >=10 threshold here too
            # (instead of only when *deciding* whether to leave a node)
            # made a collector abandon a delivery the instant transfer's
            # 5/turn rate dragged it back under 10, repeatedly choosing
            # "go collect a little more" over "finish dropping off what
            # I'm already carrying." Harmless when the relay target is
            # close by, but turned a long round trip (e.g. banking near
            # spawn from the far side of the map) into permanently
            # incomplete deliveries that never freed up enough budget to
            # fund anything else.
            if relay_target is not None and c.position == relay_target and c.azn > 0:
                c.transfer_to(relay_target)
            elif relay_target is not None and c.azn >= 10:
                c.move_to(relay_target)
            elif nearest_azn is not None:
                if c.position == nearest_azn.position:
                    c.collect_from(nearest_azn.position)
                else:
                    c.move_to(nearest_azn.position)
            elif relay_target is not None and c.azn > 0:
                c.move_to(relay_target)

        if fighter is None:
            return
        nearest_enemy = self._nearest_enemy(map_info, fighter.position)
        if nearest_enemy is None:
            fighter.stop()
            return
        enemy_pos = tuple(nearest_enemy["position"])
        dist = math.hypot(fighter.position[0] - enemy_pos[0], fighter.position[1] - enemy_pos[1])
        if dist <= ATTACK_RANGE:
            fighter.defend(enemy_pos)
        else:
            fighter.move_to(enemy_pos)

    # --- helpers ---

    @staticmethod
    def _needle_at(needles: list[BotProxy], pos: tuple[int, int] | None) -> BotProxy | None:
        if pos is None:
            return None
        for n in needles:
            if n.position == pos:
                return n
        return None

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

    def _second_point(self, map_info: MapInfo) -> HabitasPointInfo | None:
        from_pos = self._spawn_pos or (0, 0)
        by_dist = sorted(
            (hp for hp in map_info.habitas_points if hp.position != self._point1),
            key=lambda hp: abs(hp.position[0] - from_pos[0]) + abs(hp.position[1] - from_pos[1]),
        )
        return by_dist[0] if by_dist else None

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
    def _chokepoint(needle_pos: tuple[int, int], map_info: MapInfo) -> tuple[int, int]:
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
