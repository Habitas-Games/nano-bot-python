"""The turn loop. Mirrors src/core/simulation_core.gd phase-for-phase:
(1) decrement timers, (2) advance movement, (3) call strategies,
(4) apply action queues, (5) resolve attacks, (6) tick auto-destruct,
(7) check NanoAI deaths, (8) update scores, (9) record frame, (10) check
end conditions. Comments below flag the few places this matters."""

from __future__ import annotations

import importlib.util
import os
import random
import time

from nanobot.core.action_request import ActionRequest, ActionType
from nanobot.core import bot_type_registry as BotTypeRegistry
from nanobot.core.grid_pathfinder import GridPathfinder
from nanobot.core.map_data import MapData
from nanobot.core.match_log import MatchLog
from nanobot.core.nanobot_data import NanoBotData
from nanobot.api.map_info import MapInfo
from nanobot.api.bot_proxy import BotProxy
from nanobot.api.nano_strategy import NanoStrategy

MAX_TURNS = 1500
STRATEGY_TIMEOUT_MS = 50


def _load_strategy_instance(path: str) -> NanoStrategy | None:
    """Load a participant's .py strategy file and instantiate its NanoStrategy subclass."""
    if not path:
        return None
    if not os.path.exists(path):
        print(f"SimulationCore: strategy file not found: {path}")
        return None

    module_name = f"_nanobot_strategy_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        print(f"SimulationCore: failed to load strategy: {path}")
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"SimulationCore: error executing strategy {path}: {e}")
        return None

    # Restrict to classes actually *defined* in this file (attr.__module__
    # matches), not ones merely visible in its namespace via an import —
    # otherwise a strategy file that does e.g. `from shared import
    # BaseStrategy` where BaseStrategy itself subclasses NanoStrategy would
    # see that as a second candidate too.
    #
    # A GDScript file structurally *is* exactly one class (extends
    # NanoStrategy directly), so this whole ambiguity can't arise in the
    # Godot original — it's specific to Python allowing multiple classes
    # per file. dir(module) also returns names in *sorted* order, not
    # definition order, so picking "the first one found" would silently
    # and non-obviously prefer whichever class name happens to sort first
    # alphabetically — e.g. a leftover draft class a participant forgot to
    # delete could silently win over their real strategy with no warning
    # at all. Fail loudly instead: if there's more than one candidate, that
    # is a participant error, not a guess for this loader to make for them.
    candidates = [
        getattr(module, name) for name in dir(module)
        if isinstance(getattr(module, name), type)
        and issubclass(getattr(module, name), NanoStrategy)
        and getattr(module, name) is not NanoStrategy
        and getattr(module, name).__module__ == module.__name__
    ]

    if not candidates:
        print(f"SimulationCore: no NanoStrategy subclass found in: {path}")
        return None

    if len(candidates) > 1:
        names = ", ".join(c.__name__ for c in candidates)
        print(f"SimulationCore: multiple NanoStrategy subclasses found in {path} "
              f"({names}) — a strategy file must define exactly one")
        return None

    try:
        return candidates[0]()
    except Exception as e:
        print(f"SimulationCore: error instantiating strategy {path}: {e}")
        return None


class SimulationCore:
    def __init__(self, map_data: MapData, strategy_paths: list[str], seed: int = 0):
        self._map = map_data
        self._strategy_paths = strategy_paths
        self._pathfinder = GridPathfinder(map_data)
        self._rng = random.Random(seed)
        self._player_count = max(len(strategy_paths), 2)

        self._bots: list[NanoBotData] = []
        self._next_bot_id = 0
        self._scores: dict[int, int] = {}
        self._nano_ai_alive: dict[int, bool] = {}
        self._player_azn_bank: dict[int, int] = {}
        self._azn_nodes: list[dict] = []
        self._habitas_state: list[dict] = []
        self._strategies: list[NanoStrategy | None] = []
        self._strategies_loaded = False

    def preload_strategies(self) -> None:
        if not self._strategies_loaded:
            self._load_strategies()

    def run(self) -> MatchLog:
        log = MatchLog()
        log.map_name = self._map.map_name
        log.player_strategies = list(self._strategy_paths)

        self._init_match_state()

        last_turn = MAX_TURNS
        for turn in range(1, MAX_TURNS + 1):
            events: list[dict] = []

            self._decrement_timers()
            self._advance_movement(events)
            self._call_strategies(turn)
            self._apply_action_queues(events)
            self._resolve_attacks(events)
            self._tick_auto_destruct(events)
            self._check_nano_ai_deaths()
            self._update_scores()

            log.record_frame(turn, dict(self._scores), self._bots,
                              self._azn_nodes, self._habitas_state, events)

            if self._check_end_conditions():
                last_turn = turn
                break

        log.total_turns = last_turn
        log.final_scores = dict(self._scores)
        log.winner_id = self._determine_winner()
        return log

    # --- initialisation ---

    def _init_match_state(self) -> None:
        # Use the map's own declared starting budget (MapData.starting_azn,
        # defaulting to 150 there) — previously hardcoded to a constant
        # unconditionally here, so a map's "starting_azn" JSON field was
        # silently never read by anyone.
        starting_azn = self._map.starting_azn

        self._azn_nodes = [
            {"position": n["position"], "quantity": n["quantity"]} for n in self._map.azn_nodes
        ]
        self._habitas_state = [
            {"position": pos, "owner": -1, "azn_stored": 0} for pos in self._map.habitas_points
        ]

        if not self._strategies_loaded:
            self._load_strategies()

        for player_id in range(self._player_count):
            self._scores[player_id] = 0
            self._nano_ai_alive[player_id] = True
            self._player_azn_bank[player_id] = starting_azn

            spawn = self._choose_injection_point(player_id)
            stats = BotTypeRegistry.get_type("NanoAI")
            bot = NanoBotData(self._next_bot_id, player_id, "NanoAI", spawn, stats)
            self._next_bot_id += 1
            self._bots.append(bot)

    def _load_strategies(self) -> None:
        self._strategies_loaded = True
        self._strategies = []
        for path in self._strategy_paths:
            self._strategies.append(_load_strategy_instance(path))
        while len(self._strategies) < self._player_count:
            self._strategies.append(None)

    def _choose_injection_point(self, player_id: int) -> tuple[int, int]:
        default_point = self._default_injection_point(player_id)
        strategy = self._strategies[player_id] if player_id < len(self._strategies) else None
        if strategy is None:
            return default_point
        map_info = self._build_map_info(player_id, 0)
        try:
            chosen = strategy.choose_injection_point(map_info)
        except Exception as e:
            print(f"SimulationCore: player {player_id} choose_injection_point raised: {e}")
            return default_point
        for zone in self._map.injection_zones:
            if zone["player"] == player_id:
                rx, ry, rw, rh = zone["rect"]
                if rx <= chosen[0] < rx + rw and ry <= chosen[1] < ry + rh \
                        and self._map.is_passable(chosen[0], chosen[1]):
                    return chosen
        return default_point

    def _default_injection_point(self, player_id: int) -> tuple[int, int]:
        for zone in self._map.injection_zones:
            if zone["player"] == player_id:
                return (zone["rect"][0], zone["rect"][1])
        corners = [
            (0, 0),
            (self._map.width - 1, self._map.height - 1),
            (self._map.width - 1, 0),
            (0, self._map.height - 1),
        ]
        return corners[player_id % len(corners)]

    # --- per-turn phases ---

    def _decrement_timers(self) -> None:
        for bot in self._bots:
            if not bot.is_alive:
                continue
            if bot.turns_until_move > 0:
                bot.turns_until_move -= 1
            if bot.auto_destruct_countdown > 0:
                bot.auto_destruct_countdown -= 1

    def _advance_movement(self, events: list[dict]) -> None:
        for bot in self._bots:
            if not bot.is_alive or bot.is_stationary:
                continue
            if bot.turns_until_move > 0 or not bot.path_remaining:
                continue

            next_cell = bot.path_remaining.pop(0)

            wall_here = self._find_enemy_wall(next_cell, bot.owner_id)
            if wall_here is not None or not self._map.is_passable(next_cell[0], next_cell[1]):
                bot.path_remaining.clear()
                events.append({"type": "path_blocked", "bot_id": bot.id, "at": [next_cell[0], next_cell[1]]})
                continue

            cost = self._map.movement_cost(bot.position, next_cell)
            if not bot.density_immune:
                blocker = self._find_enemy_blocker(next_cell, bot.owner_id)
                if blocker is not None:
                    cost += blocker.traversal_penalty
            bot.position = next_cell
            bot.turns_until_move = cost

    def _call_strategies(self, turn: int) -> None:
        for player_id in range(self._player_count):
            if not self._nano_ai_alive.get(player_id, False):
                continue
            strategy = self._strategies[player_id]
            if strategy is None:
                continue
            map_info = self._build_map_info(player_id, turn)
            proxies = self._build_proxies(player_id)
            t_start = time.perf_counter()
            try:
                strategy.what_to_do_next(map_info, proxies)
            except Exception as e:
                print(f"Player {player_id}: strategy raised an exception — turn forfeited: {e}")
                continue
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            if elapsed_ms > STRATEGY_TIMEOUT_MS:
                print(f"Player {player_id}: strategy exceeded {STRATEGY_TIMEOUT_MS} ms — turn forfeited")
                continue
            self._flush_proxies(proxies)

    def _apply_action_queues(self, events: list[dict]) -> None:
        for bot in self._bots:
            if not bot.is_alive or bot.pending_action is None:
                continue
            action = bot.pending_action
            bot.pending_action = None
            self._execute_action(bot, action, events)

    def _resolve_attacks(self, events: list[dict]) -> None:
        for bot in self._bots:
            if not bot.is_alive or bot.pending_action is None:
                continue
            if bot.pending_action.action_type != ActionType.DEFEND:
                continue
            action = bot.pending_action
            bot.pending_action = None
            stats = BotTypeRegistry.get_type(bot.type)
            max_damage = int(stats.get("max_damage", 0))
            atk_range = float(stats.get("attack_range", 0.0))
            if max_damage == 0:
                continue
            target_pos = action.target_position
            dist = ((bot.position[0] - target_pos[0]) ** 2 + (bot.position[1] - target_pos[1]) ** 2) ** 0.5
            if dist > atk_range:
                continue
            for target in self._bots:
                if target.owner_id != bot.owner_id and target.is_alive and target.position == target_pos:
                    dmg = self._rng.randint(1, max_damage)
                    target.take_damage(dmg)
                    events.append({"type": "attack", "attacker": bot.id, "target": target.id, "damage": dmg})
                    break

    def _tick_auto_destruct(self, events: list[dict]) -> None:
        for bot in self._bots:
            if bot.is_alive and bot.auto_destruct_countdown == 0:
                bot.is_alive = False
                events.append({"type": "auto_destruct", "bot_id": bot.id, "owner": bot.owner_id})

    def _check_nano_ai_deaths(self) -> None:
        for bot in self._bots:
            if bot.type == "NanoAI" and not bot.is_alive:
                if self._nano_ai_alive.get(bot.owner_id, True):
                    self._nano_ai_alive[bot.owner_id] = False

    def _update_scores(self) -> None:
        for hp in self._habitas_state:
            hp["owner"] = -1
            hp["azn_stored"] = 0

        for bot in self._bots:
            if bot.type != "NanoNeedle" or not bot.is_alive:
                continue
            for hp in self._habitas_state:
                if hp["position"] == bot.position:
                    hp["owner"] = bot.owner_id
                    hp["azn_stored"] = bot.azn_carried
                    break

        for pid in range(self._player_count):
            self._scores[pid] = 0
        for hp in self._habitas_state:
            if hp["owner"] == -1:
                continue
            owner = hp["owner"]
            azn = hp["azn_stored"]
            self._scores[owner] += (20 + 2 * azn) if azn > 0 else 5

    def _check_end_conditions(self) -> bool:
        living = 0
        for pid in range(self._player_count):
            for bot in self._bots:
                if bot.owner_id == pid and bot.is_alive:
                    living += 1
                    break
        return living <= 1

    def _determine_winner(self) -> int:
        """Highest score wins; ties broken per requirements.md SCO-04:
        (1) bots still alive, (2) AZN collected. ("(3) turns elapsed" from
        the spec is a single value for the whole match, not one per
        player, so it can never actually discriminate between two tied
        players — there is no way to "implement" it as a real tie-break,
        so it's omitted here rather than coded as a no-op.)

        Previously this just returned whichever player had the
        first-seen highest score, defaulting to player 0 on any tie —
        identical in the Godot original, which has the same gap between
        this docstring's spec and what the code did. Confirmed this
        wasn't a hypothetical: a "do nothing" strategy at 0 points used
        to literally beat another "do nothing" strategy whenever it
        happened to be listed first, with no regard for which one still
        had bots standing."""
        best_score = max(self._scores.values(), default=0)
        tied = [pid for pid, score in self._scores.items() if score == best_score]
        if len(tied) == 1:
            return tied[0]

        alive_counts = {
            pid: sum(1 for b in self._bots if b.owner_id == pid and b.is_alive)
            for pid in tied
        }
        most_alive = max(alive_counts.values())
        tied = [pid for pid in tied if alive_counts[pid] == most_alive]
        if len(tied) == 1:
            return tied[0]

        bank_counts = {pid: self._player_azn_bank.get(pid, 0) for pid in tied}
        most_banked = max(bank_counts.values())
        tied = [pid for pid in tied if bank_counts[pid] == most_banked]
        return tied[0]  # still tied after both criteria — first player_id, same as before

    # --- action handlers ---

    def _execute_action(self, bot: NanoBotData, action: ActionRequest, events: list[dict]) -> None:
        if action.action_type == ActionType.MOVE:
            self._action_move(bot, action)
        elif action.action_type == ActionType.COLLECT:
            self._action_collect(bot, action, events)
        elif action.action_type == ActionType.TRANSFER:
            self._action_transfer(bot, action, events)
        elif action.action_type == ActionType.BUILD:
            self._action_build(bot, action, events)
        elif action.action_type == ActionType.OPEN_IP:
            self._action_open_ip(bot, events)
        elif action.action_type == ActionType.STOP:
            bot.path_remaining.clear()
        elif action.action_type == ActionType.SELF_DESTRUCT:
            bot.is_alive = False
            events.append({"type": "self_destruct", "bot_id": bot.id})
        elif action.action_type == ActionType.DEFEND:
            bot.pending_action = action  # re-attach for _resolve_attacks to consume

    def _action_move(self, bot: NanoBotData, action: ActionRequest) -> None:
        if bot.is_stationary:
            return
        target = action.target_position
        if bot.position == target:
            bot.path_remaining.clear()
            bot.cached_target = target
            return
        if target == bot.cached_target and bot.path_remaining:
            return
        path = self._pathfinder.find_path(bot.position, target)
        if len(path) <= 1:
            return
        bot.path_remaining = path[1:]
        bot.cached_target = target

    def _action_collect(self, bot: NanoBotData, action: ActionRequest, events: list[dict]) -> None:
        stats = BotTypeRegistry.get_type(bot.type)
        capacity = int(stats.get("capacity", 0))
        rate = int(stats.get("transfer", 0))
        if capacity == 0 or rate == 0:
            return
        for node in self._azn_nodes:
            if node["position"] != action.target_position:
                continue
            if bot.position != action.target_position:
                return
            room = capacity - bot.azn_carried
            amount = min(rate, room, int(node["quantity"]))
            if amount <= 0:
                return
            bot.azn_carried += amount
            node["quantity"] -= amount
            events.append({"type": "azn_collected", "bot_id": bot.id, "amount": amount,
                            "node": [action.target_position[0], action.target_position[1]]})
            return

    def _action_transfer(self, bot: NanoBotData, action: ActionRequest, events: list[dict]) -> None:
        if bot.azn_carried == 0:
            return
        stats = BotTypeRegistry.get_type(bot.type)
        rate = int(stats.get("transfer", 0))
        if rate == 0:
            return

        for target in self._bots:
            if target.type != "NanoNeedle" or not target.is_alive:
                continue
            if target.owner_id != bot.owner_id or target.position != action.target_position:
                continue
            if bot.position != action.target_position:
                return
            needle_stats = BotTypeRegistry.get_type("NanoNeedle")
            cap = int(needle_stats.get("capacity", 100))
            room = cap - target.azn_carried
            amount = min(rate, bot.azn_carried, room)
            bot.azn_carried -= amount
            target.azn_carried += amount
            events.append({"type": "azn_transferred", "from": bot.id, "to": target.id, "amount": amount})
            return

        if self._is_at_injection_point(bot):
            amount = min(rate, bot.azn_carried)
            bot.azn_carried -= amount
            self._player_azn_bank[bot.owner_id] = self._player_azn_bank.get(bot.owner_id, 0) + amount
            events.append({"type": "azn_banked", "player": bot.owner_id, "amount": amount})

    def _action_build(self, bot: NanoBotData, action: ActionRequest, events: list[dict]) -> None:
        if bot.type != "NanoAI":
            events.append({"type": "build_failed", "bot_id": bot.id, "reason": "only_nano_ai_can_build"})
            return
        if not BotTypeRegistry.is_valid_type(action.build_type):
            events.append({"type": "build_failed", "bot_id": bot.id, "reason": "unknown_type"})
            return
        dist = abs(action.target_position[0] - bot.position[0]) + abs(action.target_position[1] - bot.position[1])
        if dist != 1 or not self._map.is_passable(action.target_position[0], action.target_position[1]):
            events.append({"type": "build_failed", "bot_id": bot.id, "reason": "invalid_position"})
            return
        new_stats = BotTypeRegistry.get_type(action.build_type)
        cost = int(new_stats.get("build_cost", 0))
        bank = self._player_azn_bank.get(bot.owner_id, 0)
        if bank < cost:
            events.append({"type": "build_failed", "bot_id": bot.id, "reason": "insufficient_azn",
                            "have": bank, "need": cost})
            return
        self._player_azn_bank[bot.owner_id] = bank - cost
        new_bot = self.spawn_bot(bot.owner_id, action.build_type, action.target_position)
        events.append({"type": "bot_built", "builder": bot.id, "new_bot": new_bot.id,
                        "type_name": action.build_type, "cost": cost})

    def _action_open_ip(self, bot: NanoBotData, events: list[dict]) -> None:
        if bot.type != "NanoIPCreator":
            return
        events.append({"type": "injection_point_created", "player": bot.owner_id,
                        "pos": [bot.position[0], bot.position[1]]})

    # --- helpers ---

    def _build_map_info(self, player_id: int, turn: int) -> MapInfo:
        return MapInfo.build(self._map, turn, self._habitas_state, self._azn_nodes,
                              self._bots, player_id, self._player_azn_bank.get(player_id, 0))

    def _build_proxies(self, player_id: int) -> list[BotProxy]:
        return [BotProxy(bot) for bot in self._bots if bot.owner_id == player_id and bot.is_alive]

    def _flush_proxies(self, proxies: list[BotProxy]) -> None:
        for proxy in proxies:
            action = proxy.flush_action()
            if action is not None:
                proxy._bot.pending_action = action

    def _find_enemy_wall(self, cell: tuple[int, int], owner_id: int) -> NanoBotData | None:
        for bot in self._bots:
            if bot.type == "NanoWall" and bot.is_alive and bot.owner_id != owner_id:
                if bot.position == cell:
                    return bot
        return None

    def _find_enemy_blocker(self, cell: tuple[int, int], owner_id: int) -> NanoBotData | None:
        for bot in self._bots:
            if bot.type == "NanoBlocker" and bot.is_alive and bot.owner_id != owner_id:
                if bot.position == cell:
                    return bot
        return None

    def _is_at_injection_point(self, bot: NanoBotData) -> bool:
        for zone in self._map.injection_zones:
            if zone["player"] == bot.owner_id:
                rx, ry, rw, rh = zone["rect"]
                if rx <= bot.position[0] < rx + rw and ry <= bot.position[1] < ry + rh:
                    return True
        return False

    def spawn_bot(self, owner_id: int, bot_type: str, position: tuple[int, int]) -> NanoBotData | None:
        stats = BotTypeRegistry.get_type(bot_type)
        if not stats:
            print(f"SimulationCore: unknown bot type '{bot_type}'")
            return None
        bot = NanoBotData(self._next_bot_id, owner_id, bot_type, position, stats)
        self._next_bot_id += 1
        self._bots.append(bot)
        return bot

    def get_pathfinder(self) -> GridPathfinder:
        return self._pathfinder
