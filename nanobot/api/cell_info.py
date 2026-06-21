"""Read-only cell snapshot for participant code. Mirrors src/api/cell_info.gd."""

from __future__ import annotations

from dataclasses import dataclass

from nanobot.core.map_data import Density, MapData, StreamDir


@dataclass
class CellInfo:
    position: tuple[int, int]
    density: Density
    stream_direction: StreamDir
    is_bone: bool

    @staticmethod
    def from_map(map_data: MapData, x: int, y: int) -> "CellInfo":
        cell = map_data.get_cell(x, y)
        density = cell["density"]
        return CellInfo(
            position=(x, y),
            density=density,
            stream_direction=cell["stream_dir"],
            is_bone=(density == Density.BONE),
        )
