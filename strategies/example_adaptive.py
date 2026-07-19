"""The advanced demo — the one that actually reads the map and adapts.

Every other example plays its one idea regardless of what's happening.
This one changes what it does based on what it can see, and it is the
only strategy that does the third thing on this list:

  1. **Scouts.** A NanoExplorer (scan 30) is built early and parked on
     the needle as a watchtower. Under fog of war you cannot react to
     what you cannot see — enemies and white cells only appear in
     `map_info.visible_enemies` / `map_info.hazards` inside a friendly
     bot's scan radius, and everything except the Explorer and the
     IPCreator is nearly blind.
  2. **Defends reactively.** The moment the watchtower spots an armed
     raider closing on a needle, the NanoAI drops a NanoWall on the
     firing line (builds resolve before attacks, so the wall beats the
     shot) and the collector shoots back. Measured across this
     project's tournaments, a compact needle-hugging defence is the
     only thing that reliably beats `example_combat`.
  3. **Clears white cells.** `defend()` works on hazards, not just
     enemy bots — and hazards never respawn. A patrol sitting on your
     supply line is a permanent tax; ~15-25 turns of collector fire
     removes it permanently. No other example does this, which is why
     they all just eat the damage forever.
  4. **Expands when it's safe to.** Once the first point is fed and
     defended and nothing is threatening it, it claims a second
     Habitas Point — two needles out-score one fortified needle
     (double the 20-point base). It expands only while unthreatened,
     because two needles are much harder to defend.

The order matters: survive first, then expand. Expanding while under
pressure is how `example_full_roster` loses to aggression.
"""

from __future__ import annotations

import heapq
import math

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.api.map_info import MapInfo
from nanobot.api.nano_strategy import NanoStrategy
from nanobot.api.reactive_defense import ReactiveDefenseMixin
from nanobot.core.map_data import Density, StreamDir

# Real movement costs (participant guide §4) — what a step actually costs,
# as opposed to the straight-line guess every other example uses.
_DENSITY_COST = {Density.LOW: 2, Density.MEDIUM: 3, Density.HIGH: 4}
_STREAM_VEC = {StreamDir.NORTH: (0, -1), StreamDir.SOUTH: (0, 1),
               StreamDir.EAST: (1, 0), StreamDir.WEST: (-1, 0)}
ROUTE_CACHE_TURNS = 25     # recompute the cost field this often

BUILD_COLLECTOR_COST = 20
BUILD_NEEDLE_COST = 40
ATTACK_RANGE = 12          # NanoCollector reach (data/bot_types.json)
HAZARD_GUARD_RADIUS = 18   # only bother clearing white cells this near our needles
EXPAND_RESERVE = 70        # bank this much before committing to a second needle
MAX_NEEDLES = 2


class ExampleAdaptive(ReactiveDefenseMixin, NanoStrategy):
    def __init__(self) -> None:
        self._cost_from: tuple[int, int] | None = None
        self._cost_field: dict[tuple[int, int], int] = {}
        self._cost_turn = -999
        # Each collector commits to a node until it's harvested/exhausted.
        # Re-picking every turn makes two near-equal nodes swap places as
        # the bot moves, and it oscillates forever without arriving — the
        # same trap example_explorer hit in v0.0.8.
        self._claimed_node: dict[int, tuple[int, int]] = {}

    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        return (0, 0)

    # --- real route analysis (the other half of "sophisticated") ---

    def _step_cost(self, map_info: MapInfo, frm: tuple[int, int],
                   to: tuple[int, int]) -> "int | None":
        cell = map_info.get_cell(to[0], to[1])
        if cell is None or cell.is_bone:
            return None
        cost = _DENSITY_COST.get(cell.density, 2)
        vec = _STREAM_VEC.get(cell.stream_direction)
        if vec is not None:
            move = (to[0] - frm[0], to[1] - frm[1])
            if move == vec:
                cost -= 2                      # riding the bloodstream
            elif move == (-vec[0], -vec[1]):
                cost += 2                      # swimming against it
        return max(1, cost)

    def _cost_map(self, map_info: MapInfo, origin: tuple[int, int]) -> dict:
        """Dijkstra over TRUE movement cost from `origin`.

        This is the whole point of the strategy: on a map with real
        topology, straight-line distance lies — a node 9 cells away can
        cost more to reach than one 12 cells away sitting down an open
        corridor. Every other example picks targets by Manhattan
        distance and therefore walks into detours. Cached for
        ROUTE_CACHE_TURNS so it stays far inside the 50 ms turn budget
        (a full 60x60 sweep is ~3600 cells)."""
        if (self._cost_from == origin
                and map_info.turn - self._cost_turn < ROUTE_CACHE_TURNS):
            return self._cost_field
        dist = {origin: 0}
        pq = [(0, origin)]
        w, h = map_info.size
        while pq:
            d, cur = heapq.heappop(pq)
            if d > dist.get(cur, math.inf):
                continue
            cx, cy = cur
            for nxt in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if not (0 <= nxt[0] < w and 0 <= nxt[1] < h):
                    continue
                step = self._step_cost(map_info, cur, nxt)
                if step is None:
                    continue
                nd = d + step
                if nd < dist.get(nxt, math.inf):
                    dist[nxt] = nd
                    heapq.heappush(pq, (nd, nxt))
        self._cost_from, self._cost_field, self._cost_turn = origin, dist, map_info.turn
        return dist

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        nano_ai = self._find(my_bots, "NanoAI")
        if nano_ai is None:
            return
        collectors = [b for b in my_bots if b.type == "NanoCollector" and b.is_alive]
        needles = [b for b in my_bots if b.type == "NanoNeedle" and b.is_alive]
        unclaimed = [hp for hp in map_info.habitas_points if hp.owner_id == -1]

        threatened = bool(needles) and any(
            self._def_nearest_threat(map_info, n.position) is not None for n in needles)

        # --- NanoAI: economy base -> defence -> (only when safe) expand ---
        if not collectors and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif not needles and unclaimed:
            self._claim(nano_ai, map_info, unclaimed)
        elif needles and self.needs_defense(map_info, my_bots, needles[0]):
            # Watchtower first, then reactive walls — survival before growth.
            self.run_defense_ai(map_info, nano_ai, needles[0], my_bots)
        elif len(collectors) < 2 and map_info.azn_bank >= BUILD_COLLECTOR_COST:
            self._build_adjacent(nano_ai, map_info, "NanoCollector")
        elif (len(needles) < MAX_NEEDLES and unclaimed and not threatened
              and map_info.azn_bank >= EXPAND_RESERVE):
            # Expand only while nothing is threatening us and the war
            # chest is comfortable — a second needle we can't defend is
            # worse than none.
            self._claim(nano_ai, map_info, unclaimed)
        elif needles:
            self.run_defense_ai(map_info, nano_ai, needles[0], my_bots)
        else:
            nano_ai.stop()

        if needles:
            self.park_watchtower(map_info, my_bots, needles[0])

        # --- Collectors: fight > clear the supply line > feed > harvest ---
        base = needles[0].position if needles else nano_ai.position
        for i, c in enumerate(collectors):
            if self.shoot_back(map_info, c):
                continue                                   # an armed raider outranks everything
            if needles and self._clear_hazard(map_info, c, needles):
                continue                                   # permanently de-tax the supply line
            node = self._pick_node(map_info, c, base)
            if needles:
                target = needles[i % len(needles)]
                if c.azn > 0 and (node is None or c.azn >= 10):
                    if c.position == target.position:
                        c.transfer_to(target.position)
                    else:
                        c.move_to(target.position)
                    continue
            if node is not None and c.position == node.position:
                self._claimed_node.pop(c.id, None)          # arrived: free it after this haul
            self._harvest(c, node)

    # --- the behaviour no other example has ---

    def _clear_hazard(self, map_info: MapInfo, collector: BotProxy,
                      needles: list[BotProxy]) -> bool:
        """Shoot a visible white cell that is loitering near our needles.
        Hazards never respawn, so the ~15-25 turns of fire this costs buys
        a permanently safer supply line. Returns True if it fired."""
        best, best_d = None, ATTACK_RANGE
        for hz in map_info.hazards:
            pos = hz["position"]
            # only worth it if the hazard actually threatens our territory
            if not any(self._dist(pos, n.position) <= HAZARD_GUARD_RADIUS for n in needles):
                continue
            d = self._dist(pos, collector.position)
            if d <= best_d:
                best_d, best = d, pos
        if best is not None:
            collector.defend(best)
            return True
        return False

    # --- helpers ---

    @staticmethod
    def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _find(bots: list[BotProxy], type_name: str) -> "BotProxy | None":
        for b in bots:
            if b.type == type_name and b.is_alive:
                return b
        return None

    @staticmethod
    def _harvest(collector: BotProxy, node: "AZNNodeInfo | None") -> None:
        if node is None:
            return
        if collector.position == node.position:
            collector.collect_from(node.position)
        else:
            collector.move_to(node.position)

    def _pick_node(self, map_info: MapInfo, collector: BotProxy,
                   base: tuple[int, int]) -> "AZNNodeInfo | None":
        """Cheapest live node by REAL path cost from our base — and then
        stick with it. The field is measured from the (stationary) base
        rather than the moving collector so the ranking is stable and the
        Dijkstra caches properly (both a correctness and a turn-budget
        fix)."""
        live = {n.position: n for n in map_info.azn_nodes if n.quantity > 0}
        held = self._claimed_node.get(collector.id)
        if held is not None and held in live:
            return live[held]                      # keep going
        field = self._cost_map(map_info, base)
        best, best_d = None, math.inf
        taken = {p for bid, p in self._claimed_node.items() if bid != collector.id}
        for pos, n in live.items():
            d = field.get(pos)
            if d is None:
                continue
            if pos in taken:                       # don't stack collectors on one node
                d += 40
            if d < best_d:
                best_d, best = d, n
        if best is None:
            best = next(iter(live.values()), None)
        if best is not None:
            self._claimed_node[collector.id] = best.position
        return best

    def _claim(self, nano_ai: BotProxy, map_info: MapInfo,
               unclaimed: list["HabitasPointInfo"]) -> None:
        # Claim by true travel cost too — the "nearest" point on the
        # straight line can be the one behind a wall.
        field = self._cost_map(map_info, nano_ai.position)
        target = min(unclaimed,
                     key=lambda h: field.get(h.position,
                                             10_000 + self._manhattan(nano_ai.position, h.position)))
        if self._manhattan(nano_ai.position, target.position) == 1 \
                and map_info.azn_bank >= BUILD_NEEDLE_COST:
            nano_ai.build("NanoNeedle", target.position)
            return
        stand = self._def_approach(target.position, nano_ai.position, map_info)
        if nano_ai.position != stand:
            nano_ai.move_to(stand)
        else:
            nano_ai.stop()

    def _build_adjacent(self, nano_ai: BotProxy, map_info: MapInfo, bot_type: str) -> None:
        adj = self._def_adjacent_free(nano_ai.position, map_info)
        if adj != (-1, -1):
            nano_ai.build(bot_type, adj)

    @staticmethod
    def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
