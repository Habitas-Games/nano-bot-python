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


class TestDefaultInjectionPoint:
    def test_skips_impassable_corner_within_an_otherwise_open_zone(self):
        # Confirmed on vascular_network.json (shipped until v0.0.16): a 5x5 player-0 zone
        # (0,0)-(4,4) with a Bone border that happens to seal exactly the
        # (0, 0) corner, while the rest of the zone is fully passable.
        # Spawning on an impassable cell traps the NanoAI permanently —
        # no adjacent cell is buildable, and there's no path out for
        # move_to() to find either. The fix must pick *some* passable
        # cell in the zone instead of blindly trusting the corner.
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m._cells[0]["density"] = Density.BONE  # (0, 0) only
        m.injection_zones = [{"player": 0, "rect": (0, 0, 5, 5)}, {"player": 1, "rect": (5, 5, 5, 5)}]
        sim = SimulationCore(m, [""] * 2, seed=0)
        sim._init_match_state()

        spawn = next(b.position for b in sim._bots if b.owner_id == 0)
        assert spawn != (0, 0)
        assert sim._map.is_passable(spawn[0], spawn[1])

    def test_still_uses_the_corner_when_it_is_passable(self):
        # No regression for the common case (every existing test fixture,
        # plus simple_tissue.json while it shipped): an already-passable corner
        # is used as-is, not replaced by some other cell in the zone.
        sim = make_sim()
        spawn = next(b.position for b in sim._bots if b.owner_id == 0)
        assert spawn == (0, 0)

    def test_picks_randomly_among_passable_cells_not_always_the_first(self):
        # A bone corner with several equally-valid passable cells in the
        # rest of the zone — confirms the fallback is an actual random
        # choice (varies across seeds) rather than deterministically
        # always the first one found in row-major order.
        def spawn_for_seed(seed: int) -> tuple[int, int]:
            m = MapData(10, 10)
            for cell in m._cells:
                cell["density"] = Density.LOW
            m._cells[0]["density"] = Density.BONE  # (0, 0) only
            m.injection_zones = [{"player": 0, "rect": (0, 0, 5, 5)}, {"player": 1, "rect": (5, 5, 5, 5)}]
            sim = SimulationCore(m, [""] * 2, seed=seed)
            sim._init_match_state()
            return next(b.position for b in sim._bots if b.owner_id == 0)

        spawns = {spawn_for_seed(seed) for seed in range(20)}
        assert len(spawns) > 1, "expected different seeds to pick different passable cells"
        for spawn in spawns:
            assert spawn != (0, 0)

    def test_random_choice_uses_the_match_seeded_rng(self):
        # Reproducibility matters here the same way it does for combat
        # damage rolls (_resolve_attacks already uses self._rng) — the
        # same seed must produce the same spawn point every time.
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m._cells[0]["density"] = Density.BONE
        m.injection_zones = [{"player": 0, "rect": (0, 0, 5, 5)}, {"player": 1, "rect": (5, 5, 5, 5)}]

        spawns = []
        for _ in range(3):
            sim = SimulationCore(m, [""] * 2, seed=42)
            sim._init_match_state()
            spawns.append(next(b.position for b in sim._bots if b.owner_id == 0))
        assert len(set(spawns)) == 1

    def test_falls_back_to_the_corner_if_the_whole_zone_is_impassable(self):
        # A degenerate map (the entire zone is Bone) has no good answer —
        # confirms this returns the corner rather than raising, since a
        # broken map shouldn't crash match setup.
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        for y in range(3):
            for x in range(3):
                m._cells[y * m.width + x]["density"] = Density.BONE
        m.injection_zones = [{"player": 0, "rect": (0, 0, 3, 3)}, {"player": 1, "rect": (5, 5, 3, 3)}]
        sim = SimulationCore(m, [""] * 2, seed=0)
        sim._init_match_state()
        spawn = next(b.position for b in sim._bots if b.owner_id == 0)
        assert spawn == (0, 0)


class TestStartingAznFromMap:
    def test_default_map_starting_azn_seeds_every_players_bank(self):
        sim = make_sim()  # MapData defaults starting_azn to 150
        assert sim._player_azn_bank[0] == 150
        assert sim._player_azn_bank[1] == 150

    def test_custom_map_starting_azn_is_actually_used(self):
        # Previously _init_match_state() unconditionally used a hardcoded
        # module constant and never looked at the map at all — a map
        # declaring "starting_azn": 999 in its JSON would silently still
        # give every player only 150.
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m.starting_azn = 999
        m.injection_zones = [{"player": i, "rect": (0, 0, 10, 10)} for i in range(2)]
        sim = SimulationCore(m, ["", ""], seed=0)
        sim._init_match_state()
        assert sim._player_azn_bank[0] == 999
        assert sim._player_azn_bank[1] == 999


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

    def test_transfer_to_friendly_container_on_same_cell(self):
        # Confirms the fix: NanoContainer (capacity 60, transfer 5 in
        # data/bot_types.json) previously could never receive a transfer
        # at all — _action_transfer's target search only ever matched
        # NanoNeedle. "High-capacity storage for long supply chains" was
        # unreachable without this.
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        collector.azn_carried = 10
        container = sim.spawn_bot(0, "NanoContainer", (4, 4))
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), [])
        assert collector.azn_carried == 5
        assert container.azn_carried == 5

    def test_transfer_to_enemy_container_is_ignored(self):
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (4, 4))
        collector.azn_carried = 10
        enemy_container = sim.spawn_bot(1, "NanoContainer", (4, 4))
        sim._action_transfer(collector, ActionRequest.transfer((4, 4)), [])
        assert enemy_container.azn_carried == 0

    def test_transfer_does_not_target_the_acting_bot_itself(self):
        # NanoCollector and NanoContainer both now have capacity > 0 *and*
        # transfer > 0 (unlike NanoNeedle, which has transfer == 0) — the
        # generalized "any bot with capacity" target search could match
        # the acting bot against itself if not explicitly excluded,
        # turning a bank-transfer-at-injection-point into a silent
        # self-transfer no-op instead. Regression test for exactly that.
        sim = make_sim()
        collector = sim.spawn_bot(0, "NanoCollector", (1, 1))  # inside the full-map injection zone
        collector.azn_carried = 10
        bank_before = sim._player_azn_bank[0]
        sim._action_transfer(collector, ActionRequest.transfer((1, 1)), [])
        assert sim._player_azn_bank[0] == bank_before + 5
        assert collector.azn_carried == 5

    def test_container_can_relay_to_needle(self):
        # The full relay chain NanoContainer's description implies:
        # collector -> container -> needle.
        sim = make_sim()
        container = sim.spawn_bot(0, "NanoContainer", (4, 4))
        container.azn_carried = 10
        needle = sim.spawn_bot(0, "NanoNeedle", (4, 4))
        sim._action_transfer(container, ActionRequest.transfer((4, 4)), [])
        assert container.azn_carried == 5
        assert needle.azn_carried == 5


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
        sim._call_strategies(1, [])  # must not raise even with strategies[0] is None


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

    def test_fully_tied_match_falls_back_to_first_player(self):
        # Both players have equal score, equal bots-alive (1 each, from
        # make_sim()'s default NanoAI spawn), and equal AZN bank (both
        # default to the map's starting_azn) — every tie-break level in
        # SCO-04 is exhausted, so this is the one case where "first
        # player_id" is still the correct, documented outcome.
        sim = make_sim()
        sim._scores = {0: 30, 1: 30}
        assert sim._determine_winner() == 0

    def test_tied_score_broken_by_bots_still_alive(self):
        # requirements.md SCO-04: equal scores, tie-break 1 is "bots still
        # alive". Previously _determine_winner() never looked at this at
        # all — a player with zero bots left could still "win" a tied
        # score simply by being listed first.
        sim = make_sim()
        sim._scores = {0: 20, 1: 20}
        sim.spawn_bot(0, "NanoCollector", (1, 1))  # player 0: 2 bots alive (NanoAI + this)
        sim._bots[1].is_alive = False  # player 1: 0 bots alive (its only NanoAI just died)
        assert sim._determine_winner() == 0

    def test_tied_score_and_alive_count_broken_by_azn_banked(self):
        # Tie-break 1 (bots alive) is also equal here, so it must fall
        # through to tie-break 2 (AZN collected / banked).
        sim = make_sim()
        sim._scores = {0: 20, 1: 20}
        sim._player_azn_bank[0] = 50
        sim._player_azn_bank[1] = 200
        assert sim._determine_winner() == 1

    def test_winner_with_no_tie_ignores_tie_break_criteria_entirely(self):
        # A clear score leader wins regardless of bots-alive/bank — make
        # sure the tie-break machinery doesn't accidentally kick in when
        # there's no tie to break.
        sim = make_sim()
        sim._scores = {0: 100, 1: 5}
        sim._bots[0].is_alive = False  # player 0 has fewer bots and less bank...
        sim._player_azn_bank[0] = 0
        sim._player_azn_bank[1] = 999
        assert sim._determine_winner() == 0  # ...but still wins outright on score alone

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
        # MIN_MOVE_COST (1), not LOW density's 2 — density_immune skips the
        # density-based cost too (see test_density_immune_skips_density_cost),
        # and the blocker penalty is still exempted as before.
        assert mover.turns_until_move == 1

    def test_density_immune_skips_density_cost_on_high_density(self):
        # Confirms the actual bug fix: density_immune previously only
        # exempted the NanoBlocker penalty above, while still paying full
        # density-based cost like any other bot — contradicting both
        # NanoExplorer's "ignores density penalties entirely" description
        # and nanobot_data.py's own comment on the field. Verified directly
        # (not just by reading movement_cost) by comparing two bots moving
        # into the same HIGH-density cell.
        sim = make_sim()
        for cell in sim._map._cells:
            cell["density"] = Density.HIGH
        explorer = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        collector = sim.spawn_bot(0, "NanoCollector", (3, 4))
        explorer.path_remaining = [(4, 3)]
        collector.path_remaining = [(4, 4)]
        sim._advance_movement([])
        assert explorer.turns_until_move == 1   # density-immune: MIN_MOVE_COST
        assert collector.turns_until_move == 4  # HIGH density cost, paid in full

    def test_density_immune_bot_still_blocked_by_bone(self):
        # Bone is a structural barrier, not a density tier — density
        # immunity must not let a bot walk through it.
        sim = make_sim()
        sim._map._cells[sim._map.width * 3 + 4]["density"] = Density.BONE
        mover = sim.spawn_bot(0, "NanoExplorer", (3, 3))
        mover.path_remaining = [(4, 3)]
        events = []
        sim._advance_movement(events)
        assert mover.position == (3, 3)
        assert any(e["type"] == "path_blocked" for e in events)

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


class TestOpenIp:
    def test_open_ip_creates_a_usable_injection_point(self):
        # Confirms the fix: open_ip() previously only logged an event and
        # never touched anything _is_at_injection_point checks, so "creates
        # a new injection point" had zero gameplay effect — a bot standing
        # there still couldn't bank AZN. Verified end-to-end: a transfer
        # attempt at the same cell fails before open_ip() and succeeds
        # after it, not just that the zone list grew.
        m = MapData(10, 10)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m.injection_zones = [{"player": 0, "rect": (0, 0, 1, 1)}]  # tiny zone, far from (7, 7)
        sim = SimulationCore(m, [""] * 2, seed=0)
        sim._init_match_state()

        creator = sim.spawn_bot(0, "NanoIPCreator", (7, 7))
        collector = sim.spawn_bot(0, "NanoCollector", (7, 7))
        collector.azn_carried = 10

        bank_before = sim._player_azn_bank[0]
        sim._action_transfer(collector, ActionRequest.transfer((7, 7)), [])
        assert sim._player_azn_bank[0] == bank_before
        assert collector.azn_carried == 10  # untouched — (7, 7) isn't a zone yet

        events = []
        sim._action_open_ip(creator, events)
        assert any(e["type"] == "injection_point_created" for e in events)

        sim._action_transfer(collector, ActionRequest.transfer((7, 7)), [])
        assert sim._player_azn_bank[0] == bank_before + 5
        assert collector.azn_carried == 5

    def test_open_ip_only_works_for_nano_ip_creator(self):
        sim = make_sim()
        not_a_creator = sim.spawn_bot(0, "NanoCollector", (3, 3))
        zones_before = len(sim._injection_zones)
        events = []
        sim._action_open_ip(not_a_creator, events)
        assert events == []
        assert len(sim._injection_zones) == zones_before

    def test_open_ip_called_twice_from_same_spot_does_not_duplicate(self):
        sim = make_sim()
        creator = sim.spawn_bot(0, "NanoIPCreator", (5, 5))
        zones_before = len(sim._injection_zones)
        sim._action_open_ip(creator, [])
        sim._action_open_ip(creator, [])
        assert len(sim._injection_zones) == zones_before + 1

    def test_open_ip_zone_outlives_the_creator(self):
        # The created zone is a permanent map feature, not tied to the
        # creator bot's own lifetime — it auto-destructs on its own
        # countdown, but the depot it placed stays.
        m = MapData(10, 10)
        m.injection_zones = []
        sim = SimulationCore(m, [""] * 2, seed=0)
        sim._init_match_state()
        creator = sim.spawn_bot(0, "NanoIPCreator", (5, 5))
        sim._action_open_ip(creator, [])
        creator.is_alive = False
        assert any(z["rect"] == (5, 5, 1, 1) for z in sim._injection_zones)


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


class TestFogOfWar:
    def test_enemy_outside_all_scan_radii_is_invisible(self):
        sim = make_sim(width=30, height=30)
        # Player 0's only bot is its NanoAI (scan 5) at spawn (0, 0).
        enemy = sim.spawn_bot(1, "NanoCollector", (20, 20))
        mi = sim._build_map_info(0, 1)
        assert all(e["id"] != enemy.id for e in mi.visible_enemies)

    def test_enemy_inside_scan_radius_is_visible(self):
        sim = make_sim(width=30, height=30)
        enemy = sim.spawn_bot(1, "NanoCollector", (3, 3))  # dist ~4.2 <= NanoAI scan 5
        mi = sim._build_map_info(0, 1)
        assert any(e["id"] == enemy.id for e in mi.visible_enemies)

    def test_explorer_extends_vision(self):
        sim = make_sim(width=60, height=60)
        scout = sim.spawn_bot(0, "NanoExplorer", (30, 30))  # scan 30
        enemy = sim.spawn_bot(1, "NanoCollector", (50, 30))  # dist 20 from scout
        mi = sim._build_map_info(0, 1)
        assert any(e["id"] == enemy.id for e in mi.visible_enemies)

    def test_scan_floor_gives_adjacent_awareness_to_scanless_bots(self):
        sim = make_sim(width=30, height=30)
        # Move player 0's AI far away; give it a scan-0 collector with an
        # enemy standing right next to it — SCAN_FLOOR must reveal it.
        sim._bots[0].position = (25, 25)
        sim.spawn_bot(0, "NanoCollector", (10, 10))
        enemy = sim.spawn_bot(1, "NanoCollector", (11, 10))
        mi = sim._build_map_info(0, 1)
        assert any(e["id"] == enemy.id for e in mi.visible_enemies)


class TestLineOfSight:
    def test_wall_between_attacker_and_target_blocks_the_shot(self):
        sim = make_sim(width=20, height=20)
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        sim.spawn_bot(1, "NanoWall", (5, 8))  # on the segment
        target = sim.spawn_bot(1, "NanoAI", (5, 11))
        attacker.pending_action = ActionRequest.defend((5, 11))
        events = []
        sim._resolve_attacks(events)
        assert target.hp == target.max_hp
        assert any(e["type"] == "attack_blocked" for e in events)

    def test_own_wall_blocks_own_shot_too(self):
        sim = make_sim(width=20, height=20)
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        sim.spawn_bot(0, "NanoWall", (5, 8))  # attacker's own wall
        target = sim.spawn_bot(1, "NanoAI", (5, 11))
        attacker.pending_action = ActionRequest.defend((5, 11))
        sim._resolve_attacks([])
        assert target.hp == target.max_hp

    def test_bone_blocks_the_shot(self):
        sim = make_sim(width=20, height=20)
        sim._map._cells[8 * 20 + 5]["density"] = Density.BONE  # (5, 8)
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        target = sim.spawn_bot(1, "NanoAI", (5, 11))
        attacker.pending_action = ActionRequest.defend((5, 11))
        sim._resolve_attacks([])
        assert target.hp == target.max_hp

    def test_clear_line_still_hits(self):
        sim = make_sim(width=20, height=20)
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 5))
        target = sim.spawn_bot(1, "NanoAI", (5, 11))
        attacker.pending_action = ActionRequest.defend((5, 11))
        sim._resolve_attacks([])
        assert target.hp < target.max_hp

    def test_walled_in_needle_survives_a_lone_attacker(self):
        # GAME-03's acceptance criterion, direct: needle ringed by walls,
        # attacker outside the ring, every shot blocked.
        sim = make_sim(width=20, height=20)
        needle = sim.spawn_bot(1, "NanoNeedle", (10, 10))
        for cell in [(9, 10), (11, 10), (10, 9), (10, 11),
                     (9, 9), (11, 11), (9, 11), (11, 9)]:
            sim.spawn_bot(1, "NanoWall", cell)
        attacker = sim.spawn_bot(0, "NanoCollector", (10, 4))
        for _ in range(10):
            attacker.pending_action = ActionRequest.defend((10, 10))
            sim._resolve_attacks([])
        assert needle.hp == needle.max_hp


class TestHabitasExclusivity:
    def test_needle_build_on_occupied_cell_fails(self):
        sim = make_sim()
        sim.spawn_bot(1, "NanoNeedle", (4, 4))  # enemy needle already there
        builder = sim._bots[0]  # player 0's NanoAI
        builder.position = (4, 3)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(builder, ActionRequest.build("NanoNeedle", (4, 4)), events)
        assert any(e["type"] == "build_failed" and e["reason"] == "habitas_occupied" for e in events)
        assert sim._player_azn_bank[0] == 100  # no charge on failure

    def test_point_reopens_after_needle_dies(self):
        sim = make_sim()
        old = sim.spawn_bot(1, "NanoNeedle", (4, 4))
        old.is_alive = False
        builder = sim._bots[0]
        builder.position = (4, 3)
        sim._player_azn_bank[0] = 100
        events = []
        sim._action_build(builder, ActionRequest.build("NanoNeedle", (4, 4)), events)
        assert any(e["type"] == "bot_built" for e in events)


class TestHazards:
    @staticmethod
    def make_hazard_sim(path, move_every=1, damage=3, rng_range=1.5, hp=40):
        m = MapData(20, 20)
        for cell in m._cells:
            cell["density"] = Density.LOW
        m.injection_zones = [{"player": 0, "rect": (0, 0, 2, 2)},
                              {"player": 1, "rect": (18, 18, 2, 2)}]
        m.hazards = [{"path": path, "hp": hp, "damage": damage,
                      "range": rng_range, "move_every": move_every}]
        sim = SimulationCore(m, [""] * 2, seed=0)
        sim._init_match_state()
        return sim

    def test_hazard_patrols_toward_next_waypoint(self):
        sim = self.make_hazard_sim(path=[(5, 5), (10, 5)], move_every=1)
        for _ in range(5):
            sim._advance_hazards([])
        assert sim._hazards[0]["position"][0] > 5

    def test_hazard_attacks_nearest_bot_in_range(self):
        sim = self.make_hazard_sim(path=[(5, 5)])
        victim = sim.spawn_bot(0, "NanoCollector", (5, 6))
        events = []
        sim._advance_hazards(events)
        assert victim.hp < victim.max_hp
        assert any(e["type"] == "hazard_attack" for e in events)

    def test_hazard_kill_emits_bot_destroyed_event(self):
        sim = self.make_hazard_sim(path=[(5, 5)], damage=3)
        victim = sim.spawn_bot(0, "NanoCollector", (5, 6))
        victim.hp = 1
        events = []
        sim._advance_hazards(events)
        assert not victim.is_alive
        assert any(e["type"] == "bot_destroyed" and e["by"] == "hazard" for e in events)

    def test_wall_blocks_hazard_movement(self):
        sim = self.make_hazard_sim(path=[(5, 5), (8, 5)], move_every=1)
        sim.spawn_bot(0, "NanoWall", (6, 5))
        for _ in range(6):
            sim._advance_hazards([])
        assert sim._hazards[0]["position"] == (5, 5)  # never got past the wall

    def test_collector_can_kill_a_hazard(self):
        sim = self.make_hazard_sim(path=[(5, 5)], hp=4)
        attacker = sim.spawn_bot(0, "NanoCollector", (5, 8))
        events = []
        for _ in range(10):
            attacker.pending_action = ActionRequest.defend((5, 5))
            sim._resolve_attacks(events)
            if not sim._hazards[0]["alive"]:
                break
        assert not sim._hazards[0]["alive"]
        assert any(e["type"] == "hazard_destroyed" for e in events)

    def test_hazards_recorded_in_frames_and_fog_gated_in_map_info(self):
        sim = self.make_hazard_sim(path=[(15, 15)])
        # Far from player 0's spawn-corner NanoAI (scan 5) -> invisible.
        mi = sim._build_map_info(0, 1)
        assert mi.hazards == []
        # Give player 0 an explorer nearby -> visible.
        sim.spawn_bot(0, "NanoExplorer", (12, 12))
        mi = sim._build_map_info(0, 1)
        assert len(mi.hazards) == 1


class TestHazardMapRoundTrip:
    def test_hazards_survive_save_and_load(self, tmp_path):
        from nanobot.core import map_loader
        m = MapData(10, 10)
        m.map_name = "Hazard RT"
        m.habitas_points.append((5, 5))
        m.azn_nodes.append({"position": (2, 2), "quantity": 10})
        m.injection_zones = [{"player": 0, "rect": (0, 0, 2, 2)},
                              {"player": 1, "rect": (8, 8, 2, 2)}]
        m.hazards = [{"path": [(3, 3), (6, 3)], "hp": 40, "damage": 3,
                      "range": 1.5, "move_every": 2}]
        path = str(tmp_path / "rt.json")
        assert map_loader.save_to_file(m, path)
        reloaded = map_loader.load_from_file(path)
        assert reloaded is not None
        assert reloaded.hazards == m.hazards


class TestStrategyFailureEvents:
    """A failing strategy must be visible in the replay, not only on the
    console — the GUI's Events ticker reads these (v0.0.20)."""

    class _Crasher:
        def what_to_do_next(self, map_info, my_bots):
            raise RuntimeError("bug in my code")

    class _Sleeper:
        def what_to_do_next(self, map_info, my_bots):
            import time
            time.sleep(0.06)  # over the 50 ms budget

    def _run_one_strategy_turn(self, strategy):
        sim = make_sim()
        sim._strategies = [strategy, None]
        sim._strategies_loaded = True
        events = []
        sim._call_strategies(1, events)
        return events

    def test_exception_emits_strategy_error_event(self, capsys):
        events = self._run_one_strategy_turn(self._Crasher())
        errs = [e for e in events if e["type"] == "strategy_error"]
        assert len(errs) == 1
        assert errs[0]["player"] == 0
        assert "RuntimeError" in errs[0]["error"]
        assert "bug in my code" in errs[0]["error"]

    def test_timeout_emits_strategy_timeout_event(self, capsys):
        events = self._run_one_strategy_turn(self._Sleeper())
        touts = [e for e in events if e["type"] == "strategy_timeout"]
        assert len(touts) == 1
        assert touts[0]["player"] == 0
        assert touts[0]["ms"] > 50

    def test_healthy_strategy_emits_nothing(self):
        class Fine:
            def what_to_do_next(self, map_info, my_bots):
                pass
        events = self._run_one_strategy_turn(Fine())
        assert events == []
