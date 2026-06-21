"""Base class participants subclass. Mirrors src/api/nano_strategy.gd."""

from __future__ import annotations

from nanobot.api.map_info import MapInfo
from nanobot.api.bot_proxy import BotProxy


class NanoStrategy:
    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        """Override to pick where your NanoAI enters the map.
        map_info.turn is 0 here (pre-match). Must return a cell within the
        injection zone assigned to your player; an invalid cell falls back
        to the zone's top-left corner."""
        return (0, 0)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        """Called once per turn (up to 1500 times). Queue actions on your
        bots via the BotProxy methods. Each bot accepts only its
        last-queued action per turn. Budget: 50ms wall-clock — exceeding
        it forfeits your turn."""
        pass
