"""Starter strategy. Copy this file and edit what_to_do_next() / choose_injection_point()."""

from nanobot.api.nano_strategy import NanoStrategy
from nanobot.api.map_info import MapInfo
from nanobot.api.bot_proxy import BotProxy


class ExampleStrategy(NanoStrategy):
    def choose_injection_point(self, map_info: MapInfo) -> tuple[int, int]:
        # Inject near the centre of the map.
        return (map_info.size[0] // 2, map_info.size[1] // 2)

    def what_to_do_next(self, map_info: MapInfo, my_bots: list[BotProxy]) -> None:
        for bot in my_bots:
            # Move each bot toward the nearest Habitas Point.
            if map_info.habitas_points:
                target = map_info.habitas_points[0].position
                bot.move_to(target)
