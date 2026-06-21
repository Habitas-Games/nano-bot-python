"""Read-only per-turn map snapshot built by SimulationCore. Mirrors
src/api/map_info.gd. Fog-of-war (visible_enemies limited by scan range)
is noted as a future milestone in the Godot version too — all enemies
are visible for now in both."""

from __future__ import annotations

from nanobot.api.azn_node_info import AZNNodeInfo
from nanobot.api.cell_info import CellInfo
from nanobot.api.habitas_point_info import HabitasPointInfo
from nanobot.core.map_data import MapData
from nanobot.core.nanobot_data import NanoBotData


class MapInfo:
    def __init__(self):
        self.size: tuple[int, int] = (0, 0)
        self.turn: int = 0
        self.habitas_points: list[HabitasPointInfo] = []
        self.azn_nodes: list[AZNNodeInfo] = []
        self.visible_enemies: list[dict] = []
        self.azn_bank: int = 0
        self._map: MapData | None = None

    @staticmethod
    def build(map_data: MapData, turn_number: int, habitas_state: list[dict],
              azn_state: list[dict], all_bots: list[NanoBotData],
              friendly_owner: int, bank: int) -> "MapInfo":
        mi = MapInfo()
        mi._map = map_data
        mi.size = (map_data.width, map_data.height)
        mi.turn = turn_number
        mi.azn_bank = bank

        mi.habitas_points = [HabitasPointInfo.from_state(s) for s in habitas_state]
        mi.azn_nodes = [AZNNodeInfo.from_state(s) for s in azn_state]

        mi.visible_enemies = [
            {"id": bot.id, "type": bot.type, "position": bot.position, "hp": bot.hp}
            for bot in all_bots
            if bot.owner_id != friendly_owner and bot.is_alive
        ]

        return mi

    def get_cell(self, x: int, y: int) -> CellInfo | None:
        if not self._map.is_in_bounds(x, y):
            return None
        return CellInfo.from_map(self._map, x, y)
