"""Custom A* over the grid using directed edge costs — bloodstream
bonuses/penalties depend on travel direction through a cell, which a
plain undirected grid A* can't model. Mirrors src/core/grid_pathfinder.gd.

Uses heapq instead of the Godot version's linear-scan open list (a noted
perf shortcut there for 50x50 grids); a binary heap is the natural choice
here and is strictly faster, with identical results."""

from __future__ import annotations

import heapq
import itertools

from nanobot.core.map_data import MapData

_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]


def _h(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GridPathfinder:
    def __init__(self, map_data: MapData):
        self._map = map_data

    def find_path(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> list[tuple[int, int]]:
        """Returns the path inclusive of both ends, or [] if none / `to` is impassable."""
        if not self._map.is_passable(to_pos[0], to_pos[1]):
            return []
        if from_pos == to_pos:
            return [from_pos]

        counter = itertools.count()  # tie-breaker so heap entries are always orderable
        open_heap: list[tuple[int, int, int, tuple[int, int]]] = []
        heapq.heappush(open_heap, (_h(from_pos, to_pos), next(counter), 0, from_pos))

        g_cost = {from_pos: 0}
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {from_pos: None}

        while open_heap:
            _f, _tie, cur_g, cur = heapq.heappop(open_heap)

            if cur_g > g_cost.get(cur, float("inf")):
                continue  # stale entry

            if cur == to_pos:
                return self._reconstruct(came_from, to_pos)

            for dx, dy in _DIRS:
                nb = (cur[0] + dx, cur[1] + dy)
                if not self._map.is_passable(nb[0], nb[1]):
                    continue
                edge_cost = self._map.movement_cost(cur, nb)
                new_g = cur_g + edge_cost
                if new_g < g_cost.get(nb, float("inf")):
                    g_cost[nb] = new_g
                    came_from[nb] = cur
                    heapq.heappush(open_heap, (new_g + _h(nb, to_pos), next(counter), new_g, nb))

        return []

    @staticmethod
    def path_cost(path: list[tuple[int, int]], map_data: MapData) -> int:
        total = 0
        for i in range(1, len(path)):
            total += map_data.movement_cost(path[i - 1], path[i])
        return total

    @staticmethod
    def _reconstruct(came_from: dict, to_pos: tuple[int, int]) -> list[tuple[int, int]]:
        path = []
        cur = to_pos
        while cur is not None:
            path.append(cur)
            cur = came_from.get(cur)
        path.reverse()
        return path
