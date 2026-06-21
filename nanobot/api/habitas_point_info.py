"""Read-only Habitas Point snapshot. Mirrors src/api/habitas_point_info.gd."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HabitasPointInfo:
    position: tuple[int, int]
    owner_id: int  # -1 = unoccupied
    azn_stored: int

    @staticmethod
    def from_state(state: dict) -> "HabitasPointInfo":
        return HabitasPointInfo(
            position=state["position"],
            owner_id=state["owner"],
            azn_stored=state["azn_stored"],
        )
