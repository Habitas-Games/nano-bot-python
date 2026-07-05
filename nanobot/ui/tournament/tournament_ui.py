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
RESULTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "replays", "tournament_results.json"))

# Fixed pixel x-offsets for the leaderboard columns. The table used to be
# built with f-string padding ({name:<28}), which only lines up in a
# monospace font — draw_text renders a proportional SysFont, so every row's
# W/L/D/Pts columns wandered (verified by screenshot).
COLS = {"rank": 20, "name": 60, "wins": 290, "losses": 330, "draws": 370, "points": 415}
PODIUM_COLORS = {1: (235, 195, 90), 2: (200, 205, 215), 3: (205, 148, 95)}


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
        self.save_failed = False

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
        # Re-runnable: once a tournament finishes, Start becomes "Run
        # Again" instead of staying dead until the app restarts (the old
        # `if self.started: return` disabled it forever).
        if self.started and not self.finished:
            return
        strategies = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "*.py")))
        maps = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if len(strategies) < 2 or not maps:
            return

        self.started = True
        self.finished = False
        self.save_failed = False
        self.completed = 0
        self.total = 0
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
        # Check the return value rather than assuming success — confirmed
        # directly: a failure here (e.g. disk full) previously left the
        # screen claiming "Tournament complete... Saved to {path}" even
        # though the file was never actually written, since self.finished
        # is set above unconditionally and the draw() text below it used
        # to be unconditional too.
        self.save_failed = not self.leaderboard.save_to_file(RESULTS_PATH)

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.btn_start.handle_event(event)
        self.btn_back.handle_event(event)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((18, 20, 26))
        # State set here, not only in handle_event — otherwise the button
        # renders one event late (or never, if no events arrive).
        self.btn_start.enabled = not self.started or self.finished
        self.btn_start.text = "Run Again" if self.finished else "Start Tournament"
        self.btn_start.draw(surface)
        self.btn_back.draw(surface)

        draw_text(surface, "Tournament", (20, 70), size=20, color=(235, 235, 235))

        if not self.started:
            draw_text(surface, "Click Start Tournament to run a round-robin over strategies/*.py x maps/*.json",
                      (20, 110), size=12, color=(150, 150, 150))
            return

        if not self.finished:
            draw_text(surface, f"Running: {self.completed}/{self.total} matches complete", (20, 110), size=14)
            bar_rect = pygame.Rect(20, 135, 400, 18)
            pygame.draw.rect(surface, (45, 48, 58), bar_rect)
            if self.total > 0:
                fill_w = int(bar_rect.width * self.completed / self.total)
                pygame.draw.rect(surface, (90, 200, 120), (bar_rect.x, bar_rect.y, fill_w, bar_rect.height))
            pygame.draw.rect(surface, (90, 95, 110), bar_rect, width=1)
            # Live standings while it runs — a long tournament used to be
            # a bare progress bar with nothing to watch until the end.
            self._draw_leaderboard(surface, 175, header="Standings so far")
        else:
            draw_text(surface, f"Tournament complete — {self.total} matches", (20, 110), size=14, color=(120, 230, 140))
            y = self._draw_leaderboard(surface, 145)
            if self.save_failed:
                draw_text(surface, f"Failed to save results to {RESULTS_PATH} (see console)", (20, y + 10), size=11, color=(230, 120, 100))
            else:
                draw_text(surface, f"Saved to {RESULTS_PATH}", (20, y + 10), size=11, color=(150, 150, 150))

    def _draw_leaderboard(self, surface: "pygame.Surface", y: int, header: str | None = None) -> int:
        """Fixed-column leaderboard table; returns the y below the last row.
        Ranks 1-3 get podium colors (TRN-05's top-3 summary)."""
        if header:
            draw_text(surface, header, (20, y), size=13, color=(160, 165, 180))
            y += 24
        for label, col in (("Rank", "rank"), ("Strategy", "name"), ("W", "wins"),
                            ("L", "losses"), ("D", "draws"), ("Pts", "points")):
            draw_text(surface, label, (COLS[col], y), size=13, color=(160, 165, 180))
        y += 22
        for i, entry in enumerate(self.leaderboard.get_sorted(), start=1):
            color = PODIUM_COLORS.get(i, (215, 218, 228))
            dq = " (DQ)" if entry["dq"] else ""
            draw_text(surface, str(i), (COLS["rank"], y), size=13, color=color)
            draw_text(surface, entry["name"] + dq, (COLS["name"], y), size=13, color=color)
            for col in ("wins", "losses", "draws", "points"):
                draw_text(surface, str(entry[col]), (COLS[col], y), size=13, color=color)
            y += 20
        return y
