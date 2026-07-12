"""Tournament screen: pick the competitors explicitly (add strategy
files one at a time or several per file-browser visit), then run a
round-robin over them across every shipped map. Mirrors the Godot
project's planned TRN-01..05 requirements.

The competitor list replaces the old "glob everything in strategies/"
behavior — the field is chosen, not whatever happens to be in a
folder, and files can come from anywhere on disk."""

from __future__ import annotations

import glob
import os

import pygame

from nanobot.core import user_prefs
from nanobot.tournament.leaderboard import Leaderboard
from nanobot.tournament.tournament_runner import TournamentRunner
from nanobot.ui.widgets import Button, FileBrowserModal, draw_text, get_font

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

COMPETITOR_ROW_H = 24
LIST_X = 20
LIST_TOP = 150


class TournamentScreen:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.on_back = None

        self.runner: TournamentRunner | None = None
        self.leaderboard = Leaderboard()
        self.competitors: list[str] = []
        self.completed = 0
        self.total = 0
        self.finished = False
        self.started = False
        self.save_failed = False

        self.browser = FileBrowserModal()
        self._remove_rects: list[tuple[pygame.Rect, str]] = []

        self._build_buttons()

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self._build_buttons()

    def _build_buttons(self) -> None:
        self.btn_add = Button((20, 20, 150, 36), "Add Competitors...", on_click=self._open_add_browser,
                              tooltip="Pick .py strategy files — tick several to add them all at once")
        self.btn_start = Button((180, 20, 160, 36), "Start Tournament", on_click=self._start)
        self.btn_back = Button((self.screen_size[0] - 120, 20, 100, 36), "Back", on_click=self._back)

    def _back(self) -> None:
        if self.runner:
            self.runner.abort()
        if self.on_back:
            self.on_back()

    def _open_add_browser(self) -> None:
        if self.started and not self.finished:
            return
        start = user_prefs.existing_dir("last_strategy_dir", os.path.abspath(STRATEGIES_DIR))
        self.browser.open("Add competitors (.py) — tick one or several, then Add",
                          start, (".py",), self._add_competitors, multi=True)

    def _add_competitors(self, paths: list[str]) -> None:
        for p in paths:
            if p not in self.competitors:
                self.competitors.append(p)
        if paths:
            user_prefs.update(last_strategy_dir=os.path.dirname(paths[0]))

    def _remove_competitor(self, path: str) -> None:
        if self.started and not self.finished:
            return
        self.competitors = [c for c in self.competitors if c != path]

    def _start(self) -> None:
        # Re-runnable: once a tournament finishes, Start becomes "Run
        # Again" instead of staying dead until the app restarts (the old
        # `if self.started: return` disabled it forever).
        if self.started and not self.finished:
            return
        maps = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if len(self.competitors) < 2 or not maps:
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
        self.runner.start(list(self.competitors), maps)

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
        if self.browser.handle_event(event):
            return
        self.btn_add.handle_event(event)
        self.btn_start.handle_event(event)
        self.btn_back.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, path in self._remove_rects:
                if rect.collidepoint(event.pos):
                    self._remove_competitor(path)
                    return

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((18, 20, 26))
        # State set here, not only in handle_event — otherwise the button
        # renders one event late (or never, if no events arrive).
        editing = not self.started or self.finished
        self.btn_add.enabled = editing
        self.btn_start.enabled = editing and len(self.competitors) >= 2
        self.btn_start.text = "Run Again" if self.finished else "Start Tournament"
        self.btn_add.draw(surface)
        self.btn_start.draw(surface)
        self.btn_back.draw(surface)

        draw_text(surface, "Tournament", (20, 70), size=20, color=(235, 235, 235))

        y = self._draw_competitors(surface, editing)
        self._draw_state(surface, y)
        # Drawn unconditionally, last: the browser is a setup-phase modal,
        # and the not-started branch of _draw_state returning early used
        # to skip it entirely (caught by the v0.0.17 interaction check —
        # the Add Competitors dialog opened but never rendered).
        self.browser.draw(surface, self.screen_size)

    def _draw_state(self, surface: "pygame.Surface", y: int) -> None:
        if not self.started:
            if len(self.competitors) < 2:
                draw_text(surface, "Add at least two competitor strategies to start.",
                          (20, y + 8), size=12, color=(150, 150, 150))
            else:
                n = len(self.competitors)
                maps = len(glob.glob(os.path.join(MAPS_DIR, "*.json")))
                matches = n * (n - 1) // 2 * maps
                draw_text(surface, f"Round-robin: {n} competitors x {maps} maps = {matches} matches.",
                          (20, y + 8), size=12, color=(150, 150, 150))
            return

        if not self.finished:
            draw_text(surface, f"Running: {self.completed}/{self.total} matches complete", (20, y + 8), size=14)
            bar_rect = pygame.Rect(20, y + 33, 400, 18)
            pygame.draw.rect(surface, (45, 48, 58), bar_rect)
            if self.total > 0:
                fill_w = int(bar_rect.width * self.completed / self.total)
                pygame.draw.rect(surface, (90, 200, 120), (bar_rect.x, bar_rect.y, fill_w, bar_rect.height))
            pygame.draw.rect(surface, (90, 95, 110), bar_rect, width=1)
            # Live standings while it runs — a long tournament used to be
            # a bare progress bar with nothing to watch until the end.
            self._draw_leaderboard(surface, y + 68, header="Standings so far")
        else:
            draw_text(surface, f"Tournament complete — {self.total} matches", (20, y + 8), size=14, color=(120, 230, 140))
            end_y = self._draw_leaderboard(surface, y + 38)
            if self.save_failed:
                draw_text(surface, f"Failed to save results to {RESULTS_PATH} (see console)", (20, end_y + 10), size=11, color=(230, 120, 100))
            else:
                draw_text(surface, f"Saved to {RESULTS_PATH}", (20, end_y + 10), size=11, color=(150, 150, 150))

    def _draw_competitors(self, surface: "pygame.Surface", editing: bool) -> int:
        """The chosen field, with a remove button per row while editable.
        Returns the y below the list."""
        draw_text(surface, f"Competitors ({len(self.competitors)})", (LIST_X, 110),
                  size=13, color=(160, 165, 180))
        y = 132
        self._remove_rects = []
        font = get_font(12)
        for path in self.competitors:
            name = os.path.basename(path)
            row = pygame.Rect(LIST_X, y, 300, COMPETITOR_ROW_H - 3)
            pygame.draw.rect(surface, (34, 37, 46), row, border_radius=3)
            label = font.render(name, True, (215, 218, 228))
            surface.blit(label, (row.x + 8, row.y + 3))
            # full path as a hint when it's from outside strategies/
            if os.path.dirname(os.path.abspath(path)) != os.path.abspath(STRATEGIES_DIR):
                hint = font.render(self._shorten_dir(os.path.dirname(path)), True, (120, 124, 138))
                surface.blit(hint, (row.right + 10, row.y + 3))
            if editing:
                xr = pygame.Rect(row.right - 20, row.y + 3, 15, 15)
                hovered = xr.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(surface, (90, 50, 50) if hovered else (60, 42, 46), xr, border_radius=2)
                xl = font.render("x", True, (230, 180, 180))
                surface.blit(xl, xl.get_rect(center=xr.center))
                self._remove_rects.append((xr, path))
            y += COMPETITOR_ROW_H
        if not self.competitors:
            draw_text(surface, "(none yet — use Add Competitors...)", (LIST_X, y), size=12, color=(120, 124, 138))
            y += COMPETITOR_ROW_H
        return y + 4

    @staticmethod
    def _shorten_dir(path: str, limit: int = 46) -> str:
        return path if len(path) <= limit else "..." + path[-(limit - 3):]

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
