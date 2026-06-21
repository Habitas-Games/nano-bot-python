"""Tournament screen: start a round-robin over strategies/*.py x maps/*.json,
show progress, then the leaderboard. Mirrors the Godot project's planned
TRN-01..05 requirements."""

from __future__ import annotations

import glob
import os

import pygame

from nanobot.tournament.leaderboard import Leaderboard
from nanobot.tournament.tournament_runner import TournamentRunner
from nanobot.ui.widgets import Button, draw_text

STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "strategies")
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maps")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "replays", "tournament_results.json")


class TournamentScreen:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.on_back = None

        self.runner: TournamentRunner | None = None
        self.leaderboard = Leaderboard()
        self.completed = 0
        self.total = 0
        self.finished = False
        self.started = False

        self._build_buttons()

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.btn_start = Button((20, 20, 160, 36), "Start Tournament", on_click=self._start)
        self.btn_back = Button((self.screen_size[0] - 120, 20, 100, 36), "Back", on_click=self._back)

    def _back(self) -> None:
        if self.runner:
            self.runner.abort()
        if self.on_back:
            self.on_back()

    def _start(self) -> None:
        if self.started:
            return
        strategies = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "*.py")))
        maps = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if len(strategies) < 2 or not maps:
            return

        self.started = True
        self.leaderboard = Leaderboard()
        self.runner = TournamentRunner()
        self.runner.on_progress_updated = self._on_progress
        self.runner.on_match_finished = self._on_match_finished
        self.runner.on_tournament_finished = self._on_finished
        self.runner.start(strategies, maps)

    def _on_progress(self, completed: int, total: int) -> None:
        self.completed = completed
        self.total = total

    def _on_match_finished(self, result: dict) -> None:
        self.leaderboard.add_result(result)

    def _on_finished(self) -> None:
        self.finished = True
        self.leaderboard.save_to_file(RESULTS_PATH)

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.btn_start.enabled = not self.started
        self.btn_start.handle_event(event)
        self.btn_back.handle_event(event)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((18, 20, 26))
        self.btn_start.draw(surface)
        self.btn_back.draw(surface)

        draw_text(surface, "Tournament", (20, 70), size=20, color=(235, 235, 235))

        if self.started and not self.finished:
            draw_text(surface, f"Running: {self.completed}/{self.total} matches complete", (20, 110), size=14)
            bar_rect = pygame.Rect(20, 135, 400, 18)
            pygame.draw.rect(surface, (45, 48, 58), bar_rect)
            if self.total > 0:
                fill_w = int(bar_rect.width * self.completed / self.total)
                pygame.draw.rect(surface, (90, 200, 120), (bar_rect.x, bar_rect.y, fill_w, bar_rect.height))
            pygame.draw.rect(surface, (90, 95, 110), bar_rect, width=1)

        if self.finished:
            draw_text(surface, f"Tournament complete — {self.total} matches", (20, 110), size=14, color=(120, 230, 140))
            y = 145
            draw_text(surface, f"{'Rank':<5}{'Strategy':<28}{'W':<4}{'L':<4}{'D':<4}{'Pts':<6}", (20, y), size=13, color=(160, 165, 180))
            y += 22
            for i, entry in enumerate(self.leaderboard.get_sorted(), start=1):
                dq = " (DQ)" if entry["dq"] else ""
                line = f"{i:<5}{entry['name'] + dq:<28}{entry['wins']:<4}{entry['losses']:<4}{entry['draws']:<4}{entry['points']:<6}"
                draw_text(surface, line, (20, y), size=13)
                y += 20
            draw_text(surface, f"Saved to {RESULTS_PATH}", (20, y + 10), size=11, color=(150, 150, 150))

        if not self.started:
            draw_text(surface, "Click Start Tournament to run a round-robin over strategies/*.py x maps/*.json",
                      (20, 110), size=12, color=(150, 150, 150))
