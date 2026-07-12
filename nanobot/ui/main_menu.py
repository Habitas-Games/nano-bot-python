"""Main menu screen: Run Match, Map Editor, Tournament, Quit. Mirrors the
Godot project's main_menu.gd as the app's entry screen.

Run Match opens the match workspace directly — nothing is simulated from
here anymore. The menu used to auto-run a "first match" with the first
map and first two strategies it found on disk, which meant every app
start silently committed to an arbitrary matchup before the user chose
anything; picking (and running) now happens entirely in the match
window, seeded from the last session's choices via user_prefs."""

from __future__ import annotations

import os
import webbrowser

import pygame

from nanobot.ui.widgets import Button, draw_hover_tooltips, draw_text

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
GUIDE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..",
                                            "docs", "participant_guide.html"))


def _load_image(rel_path: str) -> "pygame.Surface | None":
    path = os.path.join(ASSETS_DIR, rel_path)
    if not os.path.exists(path):
        return None
    return pygame.image.load(path)


class MainMenu:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_size = screen_size
        self.on_open_editor = None      # callback()
        self.on_open_playback = None    # callback(replay_path: str | None)
        self.on_open_tournament = None  # callback()
        self.on_quit = None             # callback()

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
        stack_h = 5 * h + 4 * gap
        y = min(int(self.screen_size[1] * 0.62), self.screen_size[1] - stack_h - 16)

        self.btn_run = Button((cx - w // 2, y, w, h), "Run Match", on_click=self._open_match_window)
        y += h + gap
        self.btn_editor = Button((cx - w // 2, y, w, h), "Map Editor", on_click=self._open_editor)
        y += h + gap
        self.btn_tournament = Button((cx - w // 2, y, w, h), "Tournament", on_click=self._open_tournament)
        y += h + gap
        self.btn_guide = Button((cx - w // 2, y, w, h), "Guide", on_click=self._open_guide,
                                tooltip="Opens the participant guide in your browser")
        y += h + gap
        self.btn_quit = Button((cx - w // 2, y, w, h), "Quit", on_click=self._quit)

        self.buttons = [self.btn_run, self.btn_editor, self.btn_tournament, self.btn_guide, self.btn_quit]

    def handle_event(self, event: "pygame.event.Event") -> None:
        for btn in self.buttons:
            btn.handle_event(event)

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
            btn.draw(surface)
        draw_hover_tooltips(surface, self.buttons)

    # --- actions ---

    def _open_match_window(self) -> None:
        if self.on_open_playback:
            self.on_open_playback(None)

    def _open_editor(self) -> None:
        if self.on_open_editor:
            self.on_open_editor()

    def _open_tournament(self) -> None:
        if self.on_open_tournament:
            self.on_open_tournament()

    def _open_guide(self) -> None:
        # The guide was only reachable by browsing the repo on disk —
        # the app itself never mentioned it existed.
        try:
            webbrowser.open("file://" + GUIDE_PATH)
        except Exception as e:
            print(f"Could not open guide: {e}")

    def _quit(self) -> None:
        if self.on_quit:
            self.on_quit()
