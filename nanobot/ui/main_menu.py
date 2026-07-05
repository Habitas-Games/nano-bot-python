"""Main menu screen: Run Match, Map Editor, Tournament, Quit. Mirrors the
Godot project's main_menu.gd as the app's entry screen.

Running a match happens on a background thread (nanobot.tournament's
TournamentRunner already established this pattern for the same reason):
a slow strategy can legitimately take up to 50ms/turn x 1500 turns x 2
players (~150s worst case) per requirements.md's STR-05 timeout budget.
Calling SimulationCore.run() directly from a button's on_click handler
blocks pygame's event loop for that whole duration with no redraw, no
progress indicator, and no way to cancel — confirmed by reading the
event loop in main.py: draw() only happens after handle_event() returns,
so a "Running..." message set inside the click handler would never
actually reach the screen before the blocking call finished anyway."""

from __future__ import annotations

import glob
import math
import os
import random
import threading
import time

import pygame

from nanobot.core.map_loader import load_from_file
from nanobot.core.simulation_core import SimulationCore
from nanobot.ui.widgets import Button, draw_text

STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "strategies")
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "maps")
REPLAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "replays")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")


def _load_image(rel_path: str) -> "pygame.Surface | None":
    path = os.path.join(ASSETS_DIR, rel_path)
    if not os.path.exists(path):
        return None
    return pygame.image.load(path)


class MainMenu:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.on_open_editor = None      # callback()
        self.on_open_playback = None    # callback(replay_path: str)
        self.on_open_tournament = None  # callback()
        self.on_quit = None             # callback()

        self.message = ""
        self.running_match = False
        self._match_thread: threading.Thread | None = None
        self._match_result: dict | None = None  # set by the thread: {"path": str} or {"error": str}
        self._match_started_at = 0.0

        # Menu art (UX-03): the background image (which has the title baked
        # into its center panel) existed in assets/ unused; the menu was a
        # flat fill + SysFont title. Falls back to the old look if missing.
        self._bg = _load_image("menu/bg_menu.png")
        self._bg_scaled: "pygame.Surface | None" = None
        self._bg_scaled_size: tuple[int, int] | None = None

        self._build_buttons()

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self._build_buttons()

    def _build_buttons(self) -> None:
        cx = self.screen_size[0] // 2
        w, h, gap = 260, 44, 14
        # Lower third: the background art carries the title in the middle
        # of the screen; buttons go below it rather than on top of it —
        # but never past the bottom edge (at 600px tall, a plain 0.66*h
        # start put Quit half off-screen, verified by screenshot).
        stack_h = 4 * h + 3 * gap
        y = min(int(self.screen_size[1] * 0.66), self.screen_size[1] - stack_h - 16)

        self.btn_run = Button((cx - w // 2, y, w, h), "Run Match", on_click=self._run_match)
        y += h + gap
        self.btn_editor = Button((cx - w // 2, y, w, h), "Map Editor", on_click=self._open_editor)
        y += h + gap
        self.btn_tournament = Button((cx - w // 2, y, w, h), "Tournament", on_click=self._open_tournament)
        y += h + gap
        self.btn_quit = Button((cx - w // 2, y, w, h), "Quit", on_click=self._quit)

        self.buttons = [self.btn_run, self.btn_editor, self.btn_tournament, self.btn_quit]

    def handle_event(self, event: "pygame.event.Event") -> None:
        if self.running_match:
            return  # ignore input while a match is in flight — nothing to click into
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt: float) -> None:
        if not self.running_match:
            return
        if self._match_thread is not None and not self._match_thread.is_alive():
            self.running_match = False
            result = self._match_result or {}
            if "error" in result:
                self.message = result["error"]
            else:
                self.message = result["summary"]
                if self.on_open_playback:
                    self.on_open_playback(result["path"])

    def draw(self, surface: "pygame.Surface") -> None:
        cx = self.screen_size[0] // 2
        if self._bg is not None:
            if self._bg_scaled_size != self.screen_size:
                self._bg_scaled = pygame.transform.smoothscale(self._bg, self.screen_size)
                self._bg_scaled_size = self.screen_size
            surface.blit(self._bg_scaled, (0, 0))
        else:
            surface.fill((18, 20, 26))
        if self._bg is not None:
            # Anchored just above the button stack rather than at a fixed
            # fraction of the screen, so the two can't overlap when the
            # stack gets pushed up on short windows.
            draw_text(surface, "Program nanobots. Conquer living tissue.",
                      (cx - 150, self.btn_run.rect.top - 34), size=14, color=(200, 205, 218))
        else:
            title_font_size = 36
            title = "nano-bot"
            draw_text(surface, title, (cx - len(title) * title_font_size // 4, 80), size=title_font_size, color=(120, 200, 140))
            draw_text(surface, "Program nanobots. Conquer living tissue.", (cx - 150, 130), size=14, color=(160, 165, 180))

        for btn in self.buttons:
            btn.enabled = not self.running_match
            btn.draw(surface)

        if self.running_match:
            self._draw_running_indicator(surface, cx)
        elif self.message:
            draw_text(surface, self.message, (cx - 200, self.screen_size[1] - 60), size=13, color=(220, 200, 120))

    def _draw_running_indicator(self, surface: "pygame.Surface", cx: int) -> None:
        elapsed = time.monotonic() - self._match_started_at
        y = self.btn_quit.rect.bottom + 50

        # A small spinning arc so a long-running match still reads as "alive,
        # not frozen" even though the underlying simulation gives no progress
        # callback (unlike the tournament runner, a single match doesn't
        # report per-turn progress — see analysis.md for why that's out of
        # scope here).
        radius = 10
        center = (cx, y)
        angle = (elapsed * 4.0) % (2 * math.pi)
        for i in range(8):
            a = angle + i * (2 * math.pi / 8)
            shade = 80 + int(150 * (i / 8))
            px = center[0] + radius * math.cos(a)
            py = center[1] + radius * math.sin(a)
            pygame.draw.circle(surface, (shade, shade, shade), (int(px), int(py)), 3)

        draw_text(surface, f"Running match... {elapsed:.1f}s", (cx - 70, y + 24), size=13, color=(220, 200, 120))

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
        if self.running_match:
            return

        # Picking the map/strategies lives entirely in the playback
        # viewer now (its "Map:"/"P1:"/"P2:" pickers + Restart), not
        # here — this button's only job is to get a first match running
        # with sensible defaults so that screen exists to pick on. Globs
        # fresh each time rather than caching a selection on the menu
        # itself, since there's no UI here to ever change it anyway.
        strategies = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "*.py")))
        maps = sorted(glob.glob(os.path.join(MAPS_DIR, "*.json")))
        if len(strategies) < 2 or not maps:
            self.message = "Need >= 2 strategies and >= 1 map to run a match"
            return

        # Prefer a matchup known to stay competitive for a full match over
        # a blind alphabetical pick — "first two alphabetically" was
        # example_combat vs example_container, a 287-turn stomp ending
        # 70-0 with player 2 wiped out (verified from last_match.json),
        # which is the worst possible first impression of the game.
        preferred = [os.path.join(STRATEGIES_DIR, n)
                     for n in ("example_explorer.py", "example_defense.py")]
        if all(p in strategies for p in preferred):
            strategies = preferred

        self.running_match = True
        self.message = ""
        self._match_result = None
        self._match_started_at = time.monotonic()
        self._match_thread = threading.Thread(
            target=self._match_worker, args=(strategies[:2], maps[0], random.randrange(1_000_000)), daemon=True)
        self._match_thread.start()

    def _match_worker(self, strategy_paths: list[str], map_path: str, seed: int) -> None:
        try:
            map_data = load_from_file(map_path)
            sim = SimulationCore(map_data, strategy_paths, seed=seed)
            log = sim.run()

            os.makedirs(REPLAYS_DIR, exist_ok=True)
            out_path = os.path.join(REPLAYS_DIR, "last_match.json")
            if not log.save_to_file(out_path):
                # save_to_file() now fails gracefully (returns False)
                # instead of raising on OSError — see match_log.py. That
                # means this method's own except-Exception below no
                # longer catches a failed save the way it used to; check
                # the return value explicitly instead, otherwise this
                # would report success and then hand a nonexistent replay
                # path to the playback viewer.
                self._match_result = {"error": f"Match ran but failed to save replay to {out_path}"}
                return

            a, b = (os.path.basename(p) for p in strategy_paths)
            self._match_result = {
                "path": out_path,
                "summary": f"{a} vs {b}: complete in {log.total_turns} turns — winner: Player {log.winner_id + 1}",
            }
        except Exception as e:
            self._match_result = {"error": f"Match failed: {e}"}
