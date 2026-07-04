"""Map data and movement-cost rules. Mirrors src/core/map_data.gd in the
Godot project byte-for-byte for the rules that matter (density cost,
bloodstream bonus/penalty, minimum move cost)."""

from __future__ import annotations

from enum import IntEnum


class Density(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    BONE = 3


class StreamDir(IntEnum):
    NONE = 0
    NORTH = 1
    SOUTH = 2
    EAST = 3
    WEST = 4


DENSITY_COST = {
    Density.LOW: 2,
    Density.MEDIUM: 3,
    Density.HIGH: 4,
}
STREAM_BONUS = 2
STREAM_PENALTY = 2
MIN_MOVE_COST = 1

_STREAM_VECTORS = {
    StreamDir.NORTH: (0, -1),
    StreamDir.SOUTH: (0, 1),
    StreamDir.EAST: (1, 0),
    StreamDir.WEST: (-1, 0),
}


class MapData:
    """Flat cell array indexed by y * width + x, matching the Godot version."""

    def __init__(self, width: int, height: int):
        self.map_name: str = ""
        self.width = width
        self.height = height
        self.starting_azn: int = 150
        self.habitas_points: list[tuple[int, int]] = []
        self.azn_nodes: list[dict] = []  # {"position": (x, y), "quantity": int}
        self.injection_zones: list[dict] = []  # {"player": int, "rect": (x, y, w, h)}
        # Immune-system hazards ("white cells") — GAME-02. Each:
        # {"path": [(x, y), ...], "hp": int, "damage": int (max per hit),
        #  "range": float (Euclidean contact range), "move_every": int}.
        # A single-point path means a stationary hazard. The path loops.
        self.hazards: list[dict] = []
        self._cells: list[dict] = [
            {"density": Density.LOW, "stream_dir": StreamDir.NONE}
            for _ in range(width * height)
        ]

    def get_cell(self, x: int, y: int) -> dict:
        return self._cells[y * self.width + x]

    def set_cell(self, x: int, y: int, density: Density, stream_dir: StreamDir) -> None:
        self._cells[y * self.width + x] = {"density": density, "stream_dir": stream_dir}

    def is_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, x: int, y: int) -> bool:
        if not self.is_in_bounds(x, y):
            return False
        return self._cells[y * self.width + x]["density"] != Density.BONE

    def movement_cost(self, from_pos: tuple[int, int], to_pos: tuple[int, int],
                       density_immune: bool = False) -> int:
        """Turns it costs to move from `from_pos` into `to_pos`. -1 if impassable.

        density_immune (NanoExplorer) skips the density-based base cost —
        Bone stays impassable regardless (that's a structural barrier, not
        a density tier) — but still feels bloodstream current, the same
        way a regular bot does."""
        if not self.is_passable(to_pos[0], to_pos[1]):
            return -1
        cell = self._cells[to_pos[1] * self.width + to_pos[0]]
        cost = MIN_MOVE_COST if density_immune else DENSITY_COST[cell["density"]]
        stream = cell["stream_dir"]
        if stream != StreamDir.NONE:
            move_dir = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])
            stream_vec = _STREAM_VECTORS.get(stream, (0, 0))
            if move_dir == stream_vec:
                cost -= STREAM_BONUS
            elif move_dir == (-stream_vec[0], -stream_vec[1]):
                cost += STREAM_PENALTY
        return max(cost, MIN_MOVE_COST)
