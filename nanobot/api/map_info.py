"""Read-only per-turn map snapshot built by SimulationCore.

Fog of war (GAME-01): `visible_enemies` and `hazards` contain only what
lies within the scan radius of at least one of *your* alive bots — the
engine computes visibility before building this snapshot, so a strategy
never sees the ground truth. Static map knowledge (terrain, Habitas
Points, AZN nodes) is always fully visible: it's anatomy, not troop
movement."""

from __future__ import annotations

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.cell_info import CellInfo
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.core.map_data import MapData


class MapInfo:
    def __init__(self):
        self.size: tuple[int, int] = (0, 0)
        self.turn: int = 0
        self.habitas_points: list[HabitasPointInfo] = []
        self.azn_nodes: list[AZNNodeInfo] = []
        self.visible_enemies: list[dict] = []  # {id, type, position, hp} — scan-limited
        self.hazards: list[dict] = []          # {id, position, hp} — scan-limited white cells
        self.azn_bank: int = 0
        self._map: MapData | None = None

    @staticmethod
    def build(map_data: MapData, turn_number: int, habitas_state: list[dict],
              azn_state: list[dict], visible_enemies: list[dict],
              hazards: list[dict], bank: int) -> "MapInfo":
        mi = MapInfo()
        mi._map = map_data
        mi.size = (map_data.width, map_data.height)
        mi.turn = turn_number
        mi.azn_bank = bank

        mi.habitas_points = [HabitasPointInfo.from_state(s) for s in habitas_state]
        mi.azn_nodes = [AZNNodeInfo.from_state(s) for s in azn_state]
        mi.visible_enemies = visible_enemies
        mi.hazards = hazards

        return mi

    def get_cell(self, x: int, y: int) -> CellInfo | None:
        if not self._map.is_in_bounds(x, y):
            return None
        return CellInfo.from_map(self._map, x, y)
