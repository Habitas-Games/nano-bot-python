"""Read-only AZN node snapshot. Mirrors src/api/azn_node_info.gd."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AZNNodeInfo:
    position: tuple[int, int]
    quantity: int

    @staticmethod
    def from_state(state: dict) -> "AZNNodeInfo":
        return AZNNodeInfo(position=state["position"], quantity=state["quantity"])
