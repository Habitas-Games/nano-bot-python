#!/usr/bin/env python3
"""nano-bot-python entry point. Launches the pygame main menu, which can
switch to the map editor, the replay/playback viewer, or the tournament
screen. Run: python main.py"""

from __future__ import annotations

import sys

import pygame

from nanobot.ui.main_menu import MainMenu
from nanobot.ui.map_editor.map_editor import MapEditorScreen
from nanobot.ui.playback.playback_viewer import PlaybackViewer
from nanobot.ui.tournament.tournament_ui import TournamentScreen

WINDOW_SIZE = (1280, 800)
FPS = 60


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("nano-bot")
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.menu = MainMenu(WINDOW_SIZE)
        self.menu.on_open_editor = self._open_editor
        self.menu.on_open_playback = self._open_playback
        self.menu.on_open_tournament = self._open_tournament
        self.menu.on_quit = self._quit

        self.editor: MapEditorScreen | None = None
        self.playback: PlaybackViewer | None = None
        self.tournament: TournamentScreen | None = None

        self.current = self.menu

    def _open_editor(self) -> None:
        if self.editor is None:
            self.editor = MapEditorScreen(self.screen.get_size())
            self.editor.on_back_to_menu = self._back_to_menu
        self.current = self.editor

    def _open_playback(self, replay_path: str) -> None:
        self.playback = PlaybackViewer(self.screen.get_size(), replay_path)
        self.playback.on_back_to_menu = self._back_to_menu
        self.current = self.playback

    def _open_tournament(self) -> None:
        if self.tournament is None:
            self.tournament = TournamentScreen(self.screen.get_size())
            self.tournament.on_back = self._back_to_menu
        self.current = self.tournament

    def _back_to_menu(self) -> None:
        self.current = self.menu

    def _quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    size = (event.w, event.h)
                    self.menu.resize(size)
                    if self.editor:
                        self.editor.resize(size)
                    if self.playback:
                        self.playback.resize(size)
                    if self.tournament:
                        self.tournament.resize(size)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.current is not self.menu:
                    # If the current screen has an open modal (e.g. the map
                    # editor's save/load dialogs), let it handle Escape
                    # itself first — its own modal-cancel logic should
                    # dismiss the modal, not jump straight past it to the
                    # main menu. Only screens with no modal open treat
                    # Escape as "go back".
                    if getattr(self.current, "modal", None) is not None:
                        self.current.handle_event(event)
                    else:
                        self.current = self.menu
                else:
                    self.current.handle_event(event)

            if hasattr(self.current, "update"):
                self.current.update(dt)

            self.current.draw(self.screen)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    App().run()
    sys.exit(0)
