"""Main menu screen: Run Match, Map Editor, Tournament, Quit. Mirrors the
Godot project's main_menu.gd as the app's entry screen."""

from __future__ import annotations

import glob
import os

import pygame

from nanobot.core.map_loader import load_from_file
from nanobot.core.simulation_core import SimulationCore
from nanobot.ui.widgets import Button, draw_text

STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "strategies")
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "maps")
REPLAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "replays")


class MainMenu:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.on_open_editor = None      # callback()
        self.on_open_playback = None    # callback(replay_path: str)
        self.on_open_tournament = None  # callback()
        self.on_quit = None             # callback()

        self.message = ""
        self._build_buttons()

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self._build_buttons()

    def _build_buttons(self) -> None:
        cx = self.screen_size[0] // 2
        w, h, gap = 260, 44, 14
        y = self.screen_size[1] // 2 - 120

        self.btn_run = Button((cx - w // 2, y, w, h), "Run Match", on_click=self._run_match)
        y += h + gap
        self.btn_editor = Button((cx - w // 2, y, w, h), "Map Editor", on_click=self._open_editor)
        y += h + gap
        self.btn_tournament = Button((cx - w // 2, y, w, h), "Tournament", on_click=self._open_tournament)
        y += h + gap
        self.btn_quit = Button((cx - w // 2, y, w, h), "Quit", on_click=self._quit)

        self.buttons = [self.btn_run, self.btn_editor, self.btn_tournament, self.btn_quit]

    def handle_event(self, event: "pygame.event.Event") -> None:
        for btn in self.buttons:
            btn.handle_event(event)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((18, 20, 26))
        title_font_size = 36
        title = "nano-bot"
        cx = self.screen_size[0] // 2
        draw_text(surface, title, (cx - len(title) * title_font_size // 4, 80), size=title_font_size, color=(120, 200, 140))
        draw_text(surface, "Program nanobots. Conquer living tissue.", (cx - 150, 130), size=14, color=(160, 165, 180))

        for btn in self.buttons:
            btn.draw(surface)

        if self.message:
            draw_text(surface, self.message, (cx - 200, self.screen_size[1] - 60), size=13, color=(220, 200, 120))

    # --- actions ---

    def _open_editor(self) -> None:
        if self.on_open_editor:
            self.on_open_editor()

    def _open_tournament(self) -> None:
        if self.on_open_tournament:
            self.on_open_tournament()

    def _quit(self) -> None:
        if self.on_quit:
            self.on_quit()

    def _run_match(self) -> None:
        strategies = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "*.py")))
        maps = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if len(strategies) < 2 or not maps:
            self.message = "Need >= 2 strategies and >= 1 map to run a match"
            return

        map_data = load_from_file(maps[0])
        sim = SimulationCore(map_data, strategies[:2], seed=0)
        self.message = f"Running {os.path.basename(strategies[0])} vs {os.path.basename(strategies[1])} ..."
        log = sim.run()

        os.makedirs(REPLAYS_DIR, exist_ok=True)
        out_path = os.path.join(REPLAYS_DIR, "last_match.json")
        log.save_to_file(out_path)
        self.message = f"Match complete in {log.total_turns} turns — winner: Player {log.winner_id}"

        if self.on_open_playback:
            self.on_open_playback(out_path)
