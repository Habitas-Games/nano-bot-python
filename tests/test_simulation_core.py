"""SimulationCore is the ported engine's center of gravity — every other
module exists to feed it or read its output. These tests drive its
private phase/action methods directly (white-box) rather than only
through full strategy files, because the interesting behavior is in
those methods (build validation, collect/transfer limits, attack
resolution, scoring) and writing a throwaway .py strategy file per
scenario would obscure what's actually being tested.

Each test builds a small SimulationCore with no real strategies
(_init_match_state() with two empty paths spawns two NanoAI and nothing
else), then manipulates _bots/_player_azn_bank/etc. directly to set up
the scenario before calling the phase method under test."""

import pytest

from nanobot.core.action_request import ActionRequest
from nanobot.core.map_data import Density, MapData
from nanobot.core.simulation_core import SimulationCore


def make_sim(width=10, height=10, players=2):
    m = MapData(width, height)
    for cell in m._cells:
        cell["density"] = Density.LOW
    m.injection_zones = [{"player": i, "rect": (0, 0, width, height)} for i in range(players)]
    sim = SimulationCore(m, [""] * players, seed=0)
    sim._init_match_state()
    return sim


class TestBuildAction:
    def test_nano_ai_can_build_adjacent_passable_cell(self):
        sim = make_sim()
        bots_before = len(sim._bots)  # 2 starting NanoAI (one per player) in a 2-player match
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 5)), events)
        assert any(e["type"] == "bot_built" for e in events)
        assert len(sim._bots) == bots_before + 1

    def test_build_deducts_cost_from_bank(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 5)), [])
        assert sim._player_azn_bank[0] == 100 - 20  # NanoCollector build_cost is 20

    def test_only_nano_ai_can_build(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (5, 5))
        bots_before = len(sim._bots)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(collector, ActionRequest.build("NanoCollector", (6, 5)), events)
        assert events[0]["reason"] == "only_nano_ai_can_build"
        assert len(sim._bots) == bots_before  # no new bot was created

    def test_unknown_bot_type_fails(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(ai, ActionRequest.build("NotARealType", (6, 5)), events)
        assert events[0]["reason"] == "unknown_type"

    def test_non_adjacent_target_fails(self):
        sim = make_sim()
        bots_before = len(sim._bots)
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (7, 5)), events)  # distance 2
        assert events[0]["reason"] == "invalid_position"
        assert len(sim._bots) == bots_before

    def test_diagonal_target_fails_even_though_visually_adjacent(self):
        # Build requires Manhattan distance exactly 1 — diagonal is distance 2.
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 6)), events)
        assert events[0]["reason"] == "invalid_position"

    def test_bone_target_fails(self):
        sim = make_sim()
        sim._map._cells[5 * 10 + 6]["density"] = Density.BONE
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 5)), events)
        assert events[0]["reason"] == "invalid_position"

    def test_insufficient_azn_fails(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 5  # NanoCollector costs 20
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 5)), events)
        assert events[0]["reason"] == "insufficient_azn"
        assert sim._player_azn_bank[0] == 5  # unchanged

    def test_exact_required_amount_succeeds(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (5, 5)
        sim._player_azn_bank[0] = 20  # exactly NanoCollector's cost
        events = []
        sim._action_build(ai, ActionRequest.build("NanoCollector", (6, 5)), events)
        assert sim._player_azn_bank[0] == 0
        assert any(e["type"] == "bot_built" for e in events)


class TestCollectAction:
    def test_collecting_while_on_node_transfers_azn(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (3, 3))
        sim._azn_nodes = [{"position": (3, 3), "quantity": 50}]
        events = []
        sim._action_collect(collector, ActionRequest.collect((3, 3)), events)
        assert collector.azn_carried == 5  # NanoCollector transfer rate is 5/turn
        assert sim._azn_nodes[0]["quantity"] == 45

    def test_collecting_while_not_on_node_does_nothing(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (3, 3))
        sim._azn_nodes = [{"position": (8, 8), "quantity": 50}]
        sim._action_collect(collector, ActionRequest.collect((8, 8)), [])
        assert collector.azn_carried == 0
        assert sim._azn_nodes[0]["quantity"] == 50

    def test_collect_is_capped_by_remaining_capacity(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (3, 3))
        collector.azn_carried = 18  # capacity is 20, room for only 2 more
        sim._azn_nodes = [{"position": (3, 3), "quantity": 50}]
        sim._action_collect(collector, ActionRequest.collect((3, 3)), [])
        assert collector.azn_carried == 20  # capped at capacity, not 18+5

    def test_collect_is_capped_by_node_quantity(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (3, 3))
        sim._azn_nodes = [{"position": (3, 3), "quantity": 2}]  # less than the transfer rate
        sim._action_collect(collector, ActionRequest.collect((3, 3)), [])
        assert collector.azn_carried == 2
        assert sim._azn_nodes[0]["quantity"] == 0

    def test_bot_type_with_no_capacity_cannot_collect(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (3, 3)
        sim._azn_nodes = [{"position": (3, 3), "quantity": 50}]
        sim._action_collect(ai, ActionRequest.collect((3, 3)), [])  # NanoAI has 0 capacity
        assert ai.azn_carried == 0


class TestTransferAction:
    def test_transfer_to_friendly_needle_on_same_cell(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        collector.azn_carried = 10
        needle = sim.spawn_bot(0, "NanoNeedle", (4, 4))
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), [])
        assert collector.azn_carried == 5  # transferred 5 (the rate), kept the rest
        assert needle.azn_carried == 5

    def test_transfer_to_enemy_needle_is_ignored(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        collector.azn_carried = 10
        enemy_needle = sim.spawn_bot(1, "NanoNeedle", (4, 4))
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), [])
        assert enemy_needle.azn_carried == 0
        # Falls through to "at injection point" check; with full-map zones in
        # make_sim(), this cell counts as player 0's injection point too.
        assert collector.azn_carried == 5

    def test_transfer_capped_by_needle_remaining_capacity(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        collector.azn_carried = 10
        needle = sim.spawn_bot(0, "NanoNeedle", (4, 4))
        needle.azn_carried = 98  # capacity 100, room for only 2 more
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), [])
        assert needle.azn_carried == 100
        assert collector.azn_carried == 8  # only gave up 2, kept the rest

    def test_transfer_with_zero_azn_carried_does_nothing(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        sim.spawn_bot(0, "NanoNeedle", (4, 4))
        events = []
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), events)
        assert events == []

    def test_transfer_to_bank_at_injection_point(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (1, 1))  # inside player 0's full-map zone
        collector.azn_carried = 10
        bank_before = sim._player_azn_bank[0]
        sim._action_transfer(collector, ActionRequest.transfer((1, 1)), [])
        assert sim._player_azn_bank[0] == bank_before + 5
        assert collector.azn_carried == 5


class TestAttackResolution:
    def test_attack_in_range_damages_enemy(self):
        sim = make_sim()
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        target = sim.spawn_bot(1, "NanoAI", (5, 6))  # distance 1, within range 12
        attacker.pending_action = ActionRequest.defend((5, 6))
        sim._resolve_attacks([])
        assert target.hp < target.max_hp

    def test_attack_out_of_range_does_nothing(self):
        sim = make_sim(width=30, height=30)
        attacker = sim.spawn_bot(0, "NanoCollector", (0, 0))
        target = sim.spawn_bot(1, "NanoAI", (25, 25))  # far beyond range 12
        attacker.pending_action = ActionRequest.defend((25, 25))
        sim._resolve_attacks([])
        assert target.hp == target.max_hp

    def test_cannot_damage_own_team(self):
        sim = make_sim()
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        friendly = sim.spawn_bot(0, "NanoAI", (5, 6))
        attacker.pending_action = ActionRequest.defend((5, 6))
        sim._resolve_attacks([])
        assert friendly.hp == friendly.max_hp

    def test_bot_type_with_zero_max_damage_cannot_attack(self):
        sim = make_sim()
        ai = sim._bots[0]  # NanoAI has max_damage 0
        ai.position = (5, 5)
        target = sim.spawn_bot(1, "NanoAI", (5, 6))
        ai.pending_action = ActionRequest.defend((5, 6))
        sim._resolve_attacks([])
        assert target.hp == target.max_hp

    def test_defend_action_is_consumed_after_resolving(self):
        sim = make_sim()
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        sim.spawn_bot(1, "NanoAI", (5, 6))
        attacker.pending_action = ActionRequest.defend((5, 6))
        sim._resolve_attacks([])
        assert attacker.pending_action is None


class TestAutoDestruct:
    def test_countdown_reaching_zero_kills_the_bot(self):
        sim = make_sim()
        wall = sim.spawn_bot(0, "NanoWall", (1, 1))
        wall.auto_destruct_countdown = 0
        events = []
        sim._tick_auto_destruct(events)
        assert wall.is_alive is False
        assert any(e["type"] == "auto_destruct" for e in events)

    def test_positive_countdown_does_not_kill(self):
        sim = make_sim()
        wall = sim.spawn_bot(0, "NanoWall", (1, 1))
        wall.auto_destruct_countdown = 5
        sim._tick_auto_destruct([])
        assert wall.is_alive is True

    def test_disabled_countdown_never_triggers(self):
        sim = make_sim()
        ai = sim._bots[0]
        assert ai.auto_destruct_countdown == -1
        sim._tick_auto_destruct([])
        assert ai.is_alive is True

    def test_decrement_timers_counts_down_toward_destruction(self):
        sim = make_sim()
        wall = sim.spawn_bot(0, "NanoWall", (1, 1))
        wall.auto_destruct_countdown = 1
        sim._decrement_timers()
        assert wall.auto_destruct_countdown == 0
        sim._tick_auto_destruct([])
        assert wall.is_alive is False


class TestNanoAIDeath:
    def test_nano_ai_death_marks_player_inactive(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.is_alive = False
        sim._check_nano_ai_deaths()
        assert sim._nano_ai_alive[0] is False

    def test_other_player_unaffected_by_one_players_nano_ai_death(self):
        sim = make_sim()
        sim._bots[0].is_alive = False
        sim._check_nano_ai_deaths()
        assert sim._nano_ai_alive[1] is True

    def test_dead_nano_ai_player_gets_no_more_strategy_calls(self):
        sim = make_sim()
        sim._bots[0].is_alive = False
        sim._check_nano_ai_deaths()
        # _call_strategies skips any player whose NanoAI is dead — verify
        # via the public effect: no exception, and nothing changes for them.
        sim._call_strategies(1)  # must not raise even with strategies[0] is None


class TestScoring:
    def test_needle_with_no_azn_scores_five(self):
        sim = make_sim()
        sim._habitas_state = [{"position": (5, 5), "owner": -1, "azn_stored": 0}]
        sim.spawn_bot(0, "NanoNeedle", (5, 5))
        sim._update_scores()
        assert sim._scores[0] == 5

    def test_needle_with_azn_scores_twenty_plus_two_per_azn(self):
        sim = make_sim()
        sim._habitas_state = [{"position": (5, 5), "owner": -1, "azn_stored": 0}]
        needle = sim.spawn_bot(0, "NanoNeedle", (5, 5))
        needle.azn_carried = 10
        sim._update_scores()
        assert sim._scores[0] == 20 + 2 * 10  # 40

    def test_unoccupied_habitas_scores_nothing(self):
        sim = make_sim()
        sim._habitas_state = [{"position": (5, 5), "owner": -1, "azn_stored": 0}]
        sim._update_scores()
        assert sim._scores[0] == 0
        assert sim._scores[1] == 0

    def test_dead_needle_does_not_score(self):
        sim = make_sim()
        sim._habitas_state = [{"position": (5, 5), "owner": -1, "azn_stored": 0}]
        needle = sim.spawn_bot(0, "NanoNeedle", (5, 5))
        needle.is_alive = False
        sim._update_scores()
        assert sim._scores[0] == 0

    def test_multiple_habitas_points_sum_for_same_player(self):
        sim = make_sim()
        sim._habitas_state = [
            {"position": (1, 1), "owner": -1, "azn_stored": 0},
            {"position": (8, 8), "owner": -1, "azn_stored": 0},
        ]
        sim.spawn_bot(0, "NanoNeedle", (1, 1))
        sim.spawn_bot(0, "NanoNeedle", (8, 8))
        sim._update_scores()
        assert sim._scores[0] == 10  # 5 + 5

    def test_scores_reset_each_call_not_accumulated(self):
        sim = make_sim()
        sim._habitas_state = [{"position": (5, 5), "owner": -1, "azn_stored": 0}]
        sim.spawn_bot(0, "NanoNeedle", (5, 5))
        sim._update_scores()
        sim._update_scores()
        sim._update_scores()
        assert sim._scores[0] == 5  # not 15 — recomputed from scratch each time


class TestEndConditionsAndWinner:
    def test_two_players_both_alive_does_not_end(self):
        sim = make_sim()
        assert sim._check_end_conditions() is False

    def test_one_player_eliminated_ends_match(self):
        sim = make_sim()
        sim._bots[0].is_alive = False  # only bot for player 0
        assert sim._check_end_conditions() is True

    def test_winner_is_highest_score(self):
        sim = make_sim()
        sim._scores = {0: 10, 1: 50}
        assert sim._determine_winner() == 1

    def test_winner_tie_breaks_to_first_player_encountered(self):
        sim = make_sim()
        sim._scores = {0: 30, 1: 30}
        assert sim._determine_winner() == 0

    def test_three_player_match_ends_when_two_eliminated(self):
        sim = make_sim(players=3)
        sim._bots[0].is_alive = False
        sim._bots[1].is_alive = False
        assert sim._check_end_conditions() is True  # only player 2 left

    def test_three_player_match_continues_with_two_alive(self):
        sim = make_sim(players=3)
        sim._bots[0].is_alive = False
        assert sim._check_end_conditions() is False  # players 1 and 2 still alive


class TestMovementAndBlocking:
    def test_move_action_queues_a_path(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (0, 0)
        sim._action_move(ai, ActionRequest.move((3, 0)))
        assert len(ai.path_remaining) > 0
        assert ai.cached_target == (3, 0)

    def test_move_to_current_position_clears_path(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.position = (3, 3)
        ai.path_remaining = [(4, 3), (5, 3)]
        sim._action_move(ai, ActionRequest.move((3, 3)))
        assert ai.path_remaining == []

    def test_stationary_bot_ignores_move_action(self):
        sim = make_sim()
        needle = sim.spawn_bot(0, "NanoNeedle", (3, 3))
        sim._action_move(needle, ActionRequest.move((8, 8)))
        assert needle.path_remaining == []

    def test_enemy_wall_blocks_movement_and_clears_path(self):
        sim = make_sim()
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        sim.spawn_bot(1, "NanoWall", (4, 3))
        mover.path_remaining = [(4, 3), (5, 3)]
        events = []
        sim._advance_movement(events)
        assert mover.position == (3, 3)  # did not move into the wall
        assert mover.path_remaining == []
        assert any(e["type"] == "path_blocked" for e in events)

    def test_friendly_wall_does_not_block_movement(self):
        sim = make_sim()
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        sim.spawn_bot(0, "NanoWall", (4, 3))  # same owner
        mover.path_remaining = [(4, 3)]
        sim._advance_movement([])
        assert mover.position == (4, 3)

    def test_enemy_blocker_adds_traversal_penalty(self):
        sim = make_sim()
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        mover.density_immune = False
        sim.spawn_bot(1, "NanoBlocker", (4, 3))
        mover.path_remaining = [(4, 3)]
        sim._advance_movement([])
        # LOW density (2) + NanoBlocker's traversal_penalty (6) = 8
        assert mover.turns_until_move == 8

    def test_density_immune_bot_ignores_blocker_penalty(self):
        sim = make_sim()
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        mover.density_immune = True
        sim.spawn_bot(1, "NanoBlocker", (4, 3))
        mover.path_remaining = [(4, 3)]
        sim._advance_movement([])
        assert mover.turns_until_move == 2  # plain LOW density cost, no penalty

    def test_bot_with_remaining_move_timer_does_not_advance(self):
        sim = make_sim()
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        mover.turns_until_move = 2
        mover.path_remaining = [(4, 3)]
        sim._advance_movement([])
        assert mover.position == (3, 3)  # still waiting out its current step


class TestStopAndSelfDestruct:
    def test_stop_clears_remaining_path(self):
        sim = make_sim()
        ai = sim._bots[0]
        ai.path_remaining = [(1, 1), (2, 2)]
        sim._execute_action(ai, ActionRequest.stop(), [])
        assert ai.path_remaining == []

    def test_self_destruct_kills_the_bot(self):
        sim = make_sim()
        ai = sim._bots[0]
        events = []
        sim._execute_action(ai, ActionRequest.self_destruct(), events)
        assert ai.is_alive is False
        assert any(e["type"] == "self_destruct" for e in events)


class TestSpawnBot:
    def test_spawn_unknown_type_returns_none_and_does_not_add_bot(self):
        sim = make_sim()
        before = len(sim._bots)
        result = sim.spawn_bot(0, "NotARealType", (1, 1))
        assert result is None
        assert len(sim._bots) == before

    def test_spawned_bots_get_unique_incrementing_ids(self):
        sim = make_sim()
        b1 = sim.spawn_bot(0, "NanoCollector", (1, 1))
        b2 = sim.spawn_bot(0, "NanoCollector", (2, 2))
        assert b2.id == b1.id + 1


class TestFullMatchRun:
    """A small full run through .run() — not white-box, exercises the
    whole turn loop end to end with no strategies at all (both players
    just sit at their NanoAI's spawn point forever)."""

    def test_match_with_no_strategies_runs_to_completion(self):
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m.injection_zones = [{"player": 0, "rect": (0, 0, 10, 10)},
                              {"player": 1, "rect": (0, 0, 10, 10)}]
        sim = SimulationCore(m, ["", ""], seed=0)
        log = sim.run()
        assert log.total_turns >= 1
        assert log.winner_id in (0, 1)
        assert len(log.frames) == log.total_turns

    def test_match_is_deterministic_for_the_same_seed(self):
        def run_once():
            m = MapData(10, 10)
            for cell in m._cells:
                cell["density"] = Density.LOW
            m.injection_zones = [{"player": 0, "rect": (0, 0, 10, 10)},
                                  {"player": 1, "rect": (0, 0, 10, 10)}]
            sim = SimulationCore(m, ["", ""], seed=42)
            return sim.run()

        log_a = run_once()
        log_b = run_once()
        assert log_a.total_turns == log_b.total_turns
        assert log_a.final_scores == log_b.final_scores
        assert log_a.winner_id == log_b.winner_id
