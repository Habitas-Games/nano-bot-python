"""Replay viewer: loads a MatchLog and renders it as an animated 2D scene
with playback controls. Mirrors the Godot project's planned VIS-01..08
requirements (docs/requirements.md §4.6) — color-coded density, animated
stream arrows, per-team bot coloring with type icons, play/pause/step/
speed controls, a HUD with turn/score/AZN/bots-alive, and click-to-inspect
on any bot."""

from __future__ import annotations

import os

import pygame

from nanobot.core.map_data import Density, MapData, StreamDir
from nanobot.core.map_loader import load_from_file
from nanobot.core.match_log import MatchLog
from nanobot.ui.widgets import Button, draw_text, get_font

CELL_SIZE = 14
SIDEBAR_WIDTH = 260
CONTROL_BAR_HEIGHT = 50
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")

DENSITY_COLOR = {
    Density.LOW: (200, 70, 70),
    Density.MEDIUM: (70, 90, 200),
    Density.HIGH: (70, 160, 80),
    Density.BONE: (15, 15, 15),
}
PLAYER_COLORS = [(64, 140, 255), (255, 77, 64), (60, 220, 110), (255, 215, 40)]
SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]


def _load_bot_sprite(bot_type: str) -> "pygame.Surface | None":
    fname = f"bot_{bot_type.lower()}.png"
    path = os.path.join(ASSETS_DIR, "bots", fname)
    if not os.path.exists(path):
        return None
    return pygame.image.load(path).convert_alpha()


class PlaybackViewer:
    def __init__(self, screen_size: tuple[int, int], replay_path: str):
        self.screen_size = screen_size
        self.log: MatchLog | None = MatchLog.load_from_file(replay_path)
        self.map: MapData | None = None
        if self.log is not None:
            map_path = self._resolve_map_path(self.log.map_name)
            self.map = load_from_file(map_path) if map_path else None
        if self.map is None:
            self.map = MapData(40, 40)  # fallback blank map so the viewer doesn't crash

        self.bot_sprites: dict[str, "pygame.Surface | None"] = {}

        self.current_frame = 0
        self.playing = False
        self.speed_index = 2  # 1.0x
        self._accum = 0.0

        self.zoom = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        self.selected_bot_id: int | None = None

        self.canvas_rect = pygame.Rect(0, CONTROL_BAR_HEIGHT, 0, 0)
        self._recompute_canvas_rect()

        self.on_back_to_menu = None  # callback()

        self._build_controls()

    def _resolve_map_path(self, map_name: str) -> str | None:
        maps_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maps")
        for fname in sorted(os.listdir(maps_dir)) if os.path.exists(maps_dir) else []:
            if not fname.endswith(".json"):
                continue
            candidate = load_from_file(os.path.join(maps_dir, fname))
            if candidate is not None and candidate.map_name == map_name:
                return os.path.join(maps_dir, fname)
        return None

    def resize(self, screen_size: tuple[int, int]) -> None:
        self.screen_size = screen_size
        self._recompute_canvas_rect()
        self._build_controls()

    def _recompute_canvas_rect(self) -> None:
        w = self.screen_size[0] - SIDEBAR_WIDTH
        h = self.screen_size[1] - CONTROL_BAR_HEIGHT
        self.canvas_rect = pygame.Rect(0, CONTROL_BAR_HEIGHT, max(0, w), max(0, h))

    def _build_controls(self) -> None:
        y = 10
        self.btn_play = Button((10, y, 70, 30), "Play", on_click=self._toggle_play)
        self.btn_step_back = Button((90, y, 30, 30), "<", on_click=lambda: self._step(-1))
        self.btn_step_fwd = Button((125, y, 30, 30), ">", on_click=lambda: self._step(1))
        self.btn_speed_down = Button((165, y, 30, 30), "-", on_click=lambda: self._change_speed(-1))
        self.btn_speed_up = Button((280, y, 30, 30), "+", on_click=lambda: self._change_speed(1))
        self.btn_back = Button((self.screen_size[0] - 110, y, 100, 30), "Back to Menu", on_click=self._back)
        self.controls = [self.btn_play, self.btn_step_back, self.btn_step_fwd,
                          self.btn_speed_down, self.btn_speed_up, self.btn_back]

    def _back(self) -> None:
        if self.on_back_to_menu:
            self.on_back_to_menu()

    def _toggle_play(self) -> None:
        self.playing = not self.playing
        self.btn_play.text = "Pause" if self.playing else "Play"

    def _step(self, delta: int) -> None:
        if self.log is None:
            return
        self.current_frame = max(0, min(len(self.log.frames) - 1, self.current_frame + delta))

    def _change_speed(self, delta: int) -> None:
        self.speed_index = max(0, min(len(SPEEDS) - 1, self.speed_index + delta))

    # --- update / events ---

    def update(self, dt: float) -> None:
        if not self.playing or self.log is None or not self.log.frames:
            return
        self._accum += dt * SPEEDS[self.speed_index]
        turns_per_second = 8.0
        while self._accum >= 1.0 / turns_per_second:
            self._accum -= 1.0 / turns_per_second
            if self.current_frame < len(self.log.frames) - 1:
                self.current_frame += 1
            else:
                self.playing = False
                self.btn_play.text = "Play"
                break

    def handle_event(self, event: "pygame.event.Event") -> None:
        for btn in self.controls:
            if btn.handle_event(event):
                return

        if event.type == pygame.MOUSEWHEEL:
            if self.canvas_rect.collidepoint(pygame.mouse.get_pos()):
                self.zoom = max(0.5, min(3.0, self.zoom + event.y * 0.1))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.canvas_rect.collidepoint(event.pos):
            self._handle_canvas_click(event.pos)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self._pan_start = event.pos
        elif event.type == pygame.MOUSEMOTION and event.buttons[1]:
            self.scroll_x -= event.rel[0]
            self.scroll_y -= event.rel[1]

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._toggle_play()
            elif event.key == pygame.K_LEFT:
                self._step(-1)
            elif event.key == pygame.K_RIGHT:
                self._step(1)

    def _handle_canvas_click(self, screen_pos: tuple[int, int]) -> None:
        if self.log is None or not self.log.frames:
            return
        frame = self.log.frames[self.current_frame]
        size = CELL_SIZE * self.zoom
        gx = (screen_pos[0] - self.canvas_rect.x + self.scroll_x) / size
        gy = (screen_pos[1] - self.canvas_rect.y + self.scroll_y) / size
        best_id, best_dist = None, 1.0
        for bot in frame["bots"]:
            bx, by = bot["pos"]
            d = ((bx + 0.5 - gx) ** 2 + (by + 0.5 - gy) ** 2) ** 0.5
            if d < best_dist:
                best_dist = d
                best_id = bot["id"]
        self.selected_bot_id = best_id

    # --- drawing ---

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill((24, 24, 28))

        pygame.draw.rect(surface, (20, 20, 24), (0, 0, self.screen_size[0], CONTROL_BAR_HEIGHT))
        for btn in self.controls:
            btn.draw(surface)
        speed_label = f"{SPEEDS[self.speed_index]}x"
        draw_text(surface, speed_label, (200, 18), size=14)

        if self.log is None or not self.log.frames:
            draw_text(surface, "No replay loaded / empty match log", (20, 70), size=16, color=(220, 100, 100))
            return

        frame = self.log.frames[self.current_frame]

        prev_clip = surface.get_clip()
        surface.set_clip(self.canvas_rect)
        self._draw_map(surface)
        self._draw_habitas(surface, frame)
        self._draw_azn(surface, frame)
        self._draw_bots(surface, frame)
        surface.set_clip(prev_clip)

        self._draw_hud(surface, frame)
        self._draw_inspector(surface, frame)

    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        size = CELL_SIZE * self.zoom
        sx = self.canvas_rect.x + x * size - self.scroll_x
        sy = self.canvas_rect.y + y * size - self.scroll_y
        return pygame.Rect(int(sx), int(sy), int(size) + 1, int(size) + 1)

    def _draw_map(self, surface: "pygame.Surface") -> None:
        for y in range(self.map.height):
            for x in range(self.map.width):
                cell = self.map._cells[y * self.map.width + x]
                r = self._cell_rect(x, y)
                if r.right < self.canvas_rect.left or r.left > self.canvas_rect.right:
                    continue
                if r.bottom < self.canvas_rect.top or r.top > self.canvas_rect.bottom:
                    continue
                pygame.draw.rect(surface, DENSITY_COLOR[cell["density"]], r)
                if cell["stream_dir"] != StreamDir.NONE:
                    self._draw_stream_arrow(surface, r, cell["stream_dir"])
                pygame.draw.rect(surface, (0, 0, 0), r, width=1)

    def _draw_stream_arrow(self, surface, r: pygame.Rect, direction: StreamDir) -> None:
        vec = {
            StreamDir.NORTH: pygame.Vector2(0, -1), StreamDir.SOUTH: pygame.Vector2(0, 1),
            StreamDir.EAST: pygame.Vector2(1, 0), StreamDir.WEST: pygame.Vector2(-1, 0),
        }[direction]
        center = pygame.Vector2(r.center)
        length = r.width * 0.35
        tip = center + vec * length
        base = center - vec * length * 0.5
        pygame.draw.line(surface, (255, 255, 255), base, tip, 2)
        perp = pygame.Vector2(-vec.y, vec.x) * 3
        head_base = tip - vec * 4
        pygame.draw.line(surface, (255, 255, 255), tip, head_base + perp, 2)
        pygame.draw.line(surface, (255, 255, 255), tip, head_base - perp, 2)

    def _draw_habitas(self, surface, frame: dict) -> None:
        for hp in frame["habitas_points"]:
            r = self._cell_rect(hp["pos"][0], hp["pos"][1])
            owner = hp["owner"]
            color = PLAYER_COLORS[owner % len(PLAYER_COLORS)] if owner >= 0 else (255, 215, 0)
            pygame.draw.circle(surface, color, r.center, r.width // 2 - 1, width=3)
            if owner >= 0 and hp["azn"] > 0:
                font = get_font(10)
                label = font.render(str(hp["azn"]), True, (255, 255, 255))
                surface.blit(label, (r.centerx - label.get_width() // 2, r.top - 12))

    def _draw_azn(self, surface, frame: dict) -> None:
        for node in frame["azn_nodes"]:
            if node["qty"] <= 0:
                continue
            r = self._cell_rect(node["pos"][0], node["pos"][1])
            pygame.draw.circle(surface, (230, 200, 60), r.center, max(3, r.width // 4))

    def _draw_bots(self, surface, frame: dict) -> None:
        for bot in frame["bots"]:
            if not bot["alive"]:
                continue
            r = self._cell_rect(bot["pos"][0], bot["pos"][1])
            sprite = self._get_sprite(bot["type"])
            color = PLAYER_COLORS[bot["owner"] % len(PLAYER_COLORS)]

            # Team color is a solid ring around the bot, not a tint blended into
            # the sprite's own colors or a tiny corner dot — both were tested
            # against red (LOW-density) terrain and were nearly invisible for
            # the red player. A ring stays legible against any background and
            # at any zoom level, and doesn't compete with the sprite's own
            # colors so the bot-type icon underneath stays readable.
            pygame.draw.circle(surface, color, r.center, r.width // 2, width=3)

            if sprite:
                # Shrink the icon slightly so the team ring isn't drawn over it.
                inset = max(2, r.width // 6)
                icon_rect = r.inflate(-inset * 2, -inset * 2)
                scaled = pygame.transform.smoothscale(sprite, icon_rect.size)
                surface.blit(scaled, icon_rect.topleft)
            else:
                font = get_font(9)
                label = font.render(bot["type"][4:6], True, color)
                surface.blit(label, label.get_rect(center=r.center))

            if bot["id"] == self.selected_bot_id:
                pygame.draw.circle(surface, (255, 255, 255), r.center, r.width // 2 + 3, width=2)

    def _get_sprite(self, bot_type: str) -> "pygame.Surface | None":
        if bot_type not in self.bot_sprites:
            self.bot_sprites[bot_type] = _load_bot_sprite(bot_type)
        return self.bot_sprites[bot_type]

    def _draw_hud(self, surface: "pygame.Surface", frame: dict) -> None:
        x = self.screen_size[0] - SIDEBAR_WIDTH
        rect = pygame.Rect(x, CONTROL_BAR_HEIGHT, SIDEBAR_WIDTH, self.screen_size[1] - CONTROL_BAR_HEIGHT)
        pygame.draw.rect(surface, (32, 32, 38), rect)
        pygame.draw.line(surface, (12, 12, 16), (x, CONTROL_BAR_HEIGHT), (x, self.screen_size[1]), 2)

        y = CONTROL_BAR_HEIGHT + 12
        draw_text(surface, f"Turn {frame['turn']} / {self.log.total_turns}", (x + 12, y), size=15, color=(235, 235, 235))
        y += 28
        draw_text(surface, "Scores", (x + 12, y), size=12, color=(160, 165, 180))
        y += 20
        for pid_str, score in sorted(frame["scores"].items(), key=lambda kv: int(kv[0])):
            pid = int(pid_str)
            color = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
            alive = sum(1 for b in frame["bots"] if b["owner"] == pid and b["alive"])
            pygame.draw.rect(surface, color, (x + 12, y + 2, 10, 10))
            draw_text(surface, f"Player {pid}: {score} pts  ({alive} bots alive)", (x + 28, y), size=12)
            y += 20

        if self.current_frame == len(self.log.frames) - 1:
            y += 8
            draw_text(surface, f"Winner: Player {self.log.winner_id}", (x + 12, y), size=14, color=(120, 230, 140))

    def _draw_inspector(self, surface: "pygame.Surface", frame: dict) -> None:
        if self.selected_bot_id is None:
            return
        bot = next((b for b in frame["bots"] if b["id"] == self.selected_bot_id), None)
        if bot is None:
            return
        x = self.screen_size[0] - SIDEBAR_WIDTH
        y = self.screen_size[1] - 140
        rect = pygame.Rect(x + 8, y, SIDEBAR_WIDTH - 16, 130)
        pygame.draw.rect(surface, (45, 48, 58), rect, border_radius=4)
        pygame.draw.rect(surface, (90, 95, 110), rect, width=1, border_radius=4)
        lines = [
            f"#{bot['id']} {bot['type']}",
            f"Owner: Player {bot['owner']}",
            f"HP: {bot['hp']}",
            f"AZN carried: {bot['azn']}",
            f"Position: {tuple(bot['pos'])}",
            f"Action: {bot['action']}",
            f"Alive: {bot['alive']}",
        ]
        for i, line in enumerate(lines):
            draw_text(surface, line, (rect.x + 8, rect.y + 8 + i * 17), size=12)
