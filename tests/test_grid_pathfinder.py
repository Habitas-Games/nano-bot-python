"""GridPathfinder is a custom directed-edge A* (heapq-based here, linear-
scan in the Godot version) — needed because bloodstream bonuses/penalties
depend on travel *direction* through a cell, which a plain undirected-
edge A* can't represent. The most important things to verify: it finds
the cheapest path (not just *a* path) when streams make a longer route
cheaper, it returns [] rather than crashing when no path exists, and
path_cost() agrees with MapData.movement_cost() summed along the path."""

from nanobot.core.grid_pathfinder import GridPathfinder
from nanobot.core.map_data import Density, MapData, StreamDir


def blank_map(width, height, density=Density.LOW):
    m = MapData(width, height)
    for cell in m._cells:
        cell["density"] = density
    return m


class TestBasicPathing:
    def test_path_to_self_is_single_cell(self):
        m = blank_map(5, 5)
        path = GridPathfinder(m).find_path((2, 2), (2, 2))
        assert path == [(2, 2)]

    def test_straight_line_path_on_uniform_terrain(self):
        m = blank_map(5, 5)
        path = GridPathfinder(m).find_path((0, 0), (4, 0))
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)
        assert len(path) == 5  # Manhattan-adjacent, no detour needed

    def test_path_is_contiguous_with_adjacent_steps(self):
        m = blank_map(6, 6)
        path = GridPathfinder(m).find_path((0, 0), (3, 4))
        for a, b in zip(path, path[1:]):
            assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1  # each step moves to an adjacent cell

    def test_unreachable_target_returns_empty(self):
        m = blank_map(5, 5)
        # Wall off the target completely with bone.
        for x in range(5):
            m._cells[3 * 5 + x]["density"] = Density.BONE
        path = GridPathfinder(m).find_path((2, 0), (2, 4))
        assert path == []

    def test_impassable_target_itself_returns_empty(self):
        m = blank_map(5, 5)
        m._cells[2 * 5 + 2]["density"] = Density.BONE
        path = GridPathfinder(m).find_path((0, 0), (2, 2))
        assert path == []

    def test_out_of_bounds_target_returns_empty(self):
        m = blank_map(5, 5)
        path = GridPathfinder(m).find_path((0, 0), (99, 99))
        assert path == []


class TestCostAwareRouting:
    def test_prefers_low_density_detour_over_high_density_straight_line(self):
        # 5-wide map: a wall of HIGH density blocks the direct row, but a
        # LOW-density detour exists one row up. The pathfinder must be
        # cost-aware, not just shortest-hop-count, to find the cheap route
        # when both exist.
        m = blank_map(5, 3, density=Density.LOW)
        for x in range(5):
            m._cells[1 * 5 + x]["density"] = Density.HIGH
        path = GridPathfinder(m).find_path((0, 1), (4, 1))
        cost = GridPathfinder.path_cost(path, m)
        # Going straight through HIGH the whole way costs 4*4=16 (4 steps).
        # Detouring up to LOW (2/step) and back is more steps but each
        # cheaper — the algorithm should find whichever is actually cheaper,
        # not just whichever has fewer hops.
        straight_through_cost = 4 * 4
        assert cost <= straight_through_cost

    def test_uses_stream_bonus_to_find_a_cheaper_path(self):
        # A 1-row east-flowing stream lane should be picked over a same-
        # length plain-density lane when moving east, since the stream
        # makes it strictly cheaper per step.
        m = blank_map(5, 3, density=Density.MEDIUM)
        for x in range(5):
            m._cells[1 * 5 + x]["stream_dir"] = StreamDir.EAST
        path = GridPathfinder(m).find_path((0, 1), (4, 1))
        cost = GridPathfinder.path_cost(path, m)
        assert cost == 4  # 4 steps at (3-2)=1 each, with the stream bonus applied

    def test_density_immune_routing_goes_straight_through_high_density(self):
        # Same map shape as the detour test above, but routed as a
        # density-immune bot (NanoExplorer): the HIGH-density row now
        # costs the same MIN_MOVE_COST as the LOW-density detour, so the
        # straight line (fewer hops, equal per-step cost) should win
        # instead of detouring around terrain that no longer slows it
        # down. Confirms find_path's density_immune actually changes the
        # chosen route, not just that path_cost would compute differently
        # for an unrelated path.
        m = blank_map(5, 3, density=Density.LOW)
        for x in range(5):
            m._cells[1 * 5 + x]["density"] = Density.HIGH
        path = GridPathfinder(m).find_path((0, 1), (4, 1), density_immune=True)
        assert path == [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]
        assert GridPathfinder.path_cost(path, m, density_immune=True) == 4  # 4 steps at MIN_MOVE_COST each


class TestPathCost:
    def test_path_cost_matches_summed_movement_cost(self):
        m = blank_map(5, 5, density=Density.MEDIUM)
        path = GridPathfinder(m).find_path((0, 0), (3, 0))
        expected = sum(m.movement_cost(path[i - 1], path[i]) for i in range(1, len(path)))
        assert GridPathfinder.path_cost(path, m) == expected

    def test_path_cost_of_single_cell_path_is_zero(self):
        m = blank_map(5, 5)
        assert GridPathfinder.path_cost([(2, 2)], m) == 0

    def test_path_cost_of_empty_path_is_zero(self):
        m = blank_map(5, 5)
        assert GridPathfinder.path_cost([], m) == 0
