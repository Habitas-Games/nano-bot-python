"""Movement cost is the single most behavior-critical formula in the whole
project — it's what every pathfinding and movement decision is built on.
Tested against the exact rule in requirements.md MAP-02/MAP-03: density
cost, then +-2 turns for moving against/with a stream, clamped to a
minimum of 1 turn."""

import pytest

from nanobot.core.map_data import Density, MapData, StreamDir


def make_map(width=5, height=5, density=Density.LOW, stream=StreamDir.NONE):
    m = MapData(width, height)
    for cell in m._cells:
        cell["density"] = density
        cell["stream_dir"] = stream
    return m


class TestBounds:
    def test_in_bounds(self):
        m = make_map(5, 5)
        assert m.is_in_bounds(0, 0)
        assert m.is_in_bounds(4, 4)

    def test_out_of_bounds(self):
        m = make_map(5, 5)
        assert not m.is_in_bounds(-1, 0)
        assert not m.is_in_bounds(0, -1)
        assert not m.is_in_bounds(5, 0)
        assert not m.is_in_bounds(0, 5)

    def test_zero_size_map_has_no_in_bounds_cells(self):
        m = MapData(0, 0)
        assert not m.is_in_bounds(0, 0)


class TestPassability:
    def test_bone_is_impassable(self):
        m = make_map(density=Density.BONE)
        assert not m.is_passable(2, 2)

    @pytest.mark.parametrize("density", [Density.LOW, Density.MEDIUM, Density.HIGH])
    def test_non_bone_is_passable(self, density):
        m = make_map(density=density)
        assert m.is_passable(2, 2)

    def test_out_of_bounds_is_not_passable(self):
        m = make_map(5, 5)
        assert not m.is_passable(-1, -1)
        assert not m.is_passable(99, 99)


class TestMovementCost:
    @pytest.mark.parametrize("density,expected", [
        (Density.LOW, 2),
        (Density.MEDIUM, 3),
        (Density.HIGH, 4),
    ])
    def test_base_density_cost_no_stream(self, density, expected):
        m = make_map(density=density)
        assert m.movement_cost((1, 1), (2, 1)) == expected

    def test_impassable_target_returns_negative_one(self):
        m = make_map(density=Density.BONE)
        assert m.movement_cost((1, 1), (2, 1)) == -1

    def test_moving_with_stream_subtracts_two(self):
        # Stream flows east; moving east (with the current) should be 2-2=... but
        # LOW density is 2, so 2-2=0, clamped to MIN_MOVE_COST=1.
        m = make_map(density=Density.LOW, stream=StreamDir.EAST)
        cost = m.movement_cost((1, 1), (2, 1))  # moving east, i.e. (+1, 0)
        assert cost == 1  # 2 - 2 = 0, clamped to minimum 1

    def test_moving_with_stream_on_higher_density(self):
        # HIGH density (4) with the stream: 4 - 2 = 2, no clamping needed.
        m = make_map(density=Density.HIGH, stream=StreamDir.EAST)
        cost = m.movement_cost((1, 1), (2, 1))
        assert cost == 2

    def test_moving_against_stream_adds_two(self):
        # Stream flows east; moving west (against the current) through this cell.
        m = make_map(density=Density.MEDIUM, stream=StreamDir.EAST)
        cost = m.movement_cost((2, 1), (1, 1))  # moving west, i.e. (-1, 0)
        assert cost == 5  # 3 + 2

    def test_moving_perpendicular_to_stream_is_unaffected(self):
        # Stream flows east; moving north/south through it shouldn't get a bonus or penalty.
        m = make_map(density=Density.MEDIUM, stream=StreamDir.EAST)
        cost = m.movement_cost((1, 2), (1, 1))  # moving north, i.e. (0, -1)
        assert cost == 3  # plain MEDIUM cost, no stream effect

    def test_minimum_cost_never_goes_below_one(self):
        # LOW (2) with the stream would be 0 without clamping.
        m = make_map(density=Density.LOW, stream=StreamDir.NORTH)
        cost = m.movement_cost((1, 1), (1, 0))  # moving north, with the stream
        assert cost >= 1

    @pytest.mark.parametrize("stream,move_delta", [
        (StreamDir.NORTH, (0, -1)),
        (StreamDir.SOUTH, (0, 1)),
        (StreamDir.EAST, (1, 0)),
        (StreamDir.WEST, (-1, 0)),
    ])
    def test_all_four_stream_directions_grant_bonus_when_moving_with_them(self, stream, move_delta):
        m = make_map(width=5, height=5, density=Density.HIGH, stream=stream)
        frm = (2, 2)  # center of the 5x5 map, so all 4 neighbors are in bounds
        to = (frm[0] + move_delta[0], frm[1] + move_delta[1])
        assert m.movement_cost(frm, to) == 2  # 4 - 2
