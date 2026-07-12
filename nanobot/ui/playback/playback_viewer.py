"""Replay viewer: loads a MatchLog and renders it as an animated 2D scene
with playback controls. Mirrors the Godot project's planned VIS-01..08
requirements (docs/requirements.md §4.6) — color-coded density, animated
stream arrows, per-team bot coloring with type icons, play/pause/step/
speed controls, a HUD with turn/score/AZN/bots-alive, and click-to-inspect
on any bot. Also doubles as the "Run Match" workspace: row 2 of the top
bar lets you change the map/strategies and re-simulate without leaving
this screen, on the same background-thread pattern main_menu.py uses for
the same reason (a strategy-heavy match can take real wall-clock time;
blocking the event loop would freeze the window with no redraw)."""

from __future__ import annotations

import glob
import math
import os
import random
import threading
import time

import pygame

from nanobot.core import bot_type_registry as BotTypeRegistry
from nanobot.core import user_prefs
from nanobot.core.map_data import Density, MapData, StreamDir
from nanobot.core.map_loader import load_from_file
from nanobot.core.match_log import MatchLog
from nanobot.core.simulation_core import SimulationCore
from nanobot.ui import icons
from nanobot.ui.widgets import (Button, FileBrowserModal, FilePickerModal, Slider,
                                draw_hover_tooltips, draw_text, get_font)

CELL_SIZE = 14
SIDEBAR_WIDTH = 260
# Row 1: playback controls (play/step/speed) + Back to Menu, unchanged.
# Row 2: map/strategy pickers + Restart — lets you change what's being
# watched and re-run without bouncing back to the main menu, which is
# the only place this used to be possible.
TOP_ROW_HEIGHT = 50
SETUP_ROW_HEIGHT = 40
CONTROL_BAR_HEIGHT = TOP_ROW_HEIGHT + SETUP_ROW_HEIGHT
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "strategies")
MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "maps")
REPLAYS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "replays")

# Fallback flat colors, used only if a texture file is missing — the real
# rendering uses the same tile/marker textures as the map editor and the
# Godot original's map_renderer.gd, not these.
DENSITY_COLOR = {
    Density.LOW: (200, 70, 70),
    Density.MEDIUM: (70, 90, 200),
    Density.HIGH: (70, 160, 80),
    Density.BONE: (15, 15, 15),
}
# Same translucent warm-dark grid as the map editor's canvas (see
# map_canvas_renderer.GRID_COLOR) instead of flat opaque black, for visual
# consistency between editing and watching the same tissue.
GRID_COLOR = (25, 12, 12, 70)
PLAYER_COLORS = [(64, 140, 255), (255, 77, 64), (60, 220, 110), (255, 215, 40)]
# Up to 16x: a full 1500-turn match at the old 4x cap took ~47s to watch;
# 16x brings "skim the whole match" down to ~12s.
SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
MIN_ZOOM, MAX_ZOOM = 0.5, 6.0
KEY_HINT = "Space play  |  Left/Right step  |  Home/End ends  |  wheel zoom  |  drag pan  |  F fit"
# How far the owned-habitas tint is lerped from the player's base color
# toward white — matches map_renderer.gd's OWNED_BLEND exactly (0.30: mostly
# the player's own color, lightly whitened so the art's shading still reads).
OWNED_BLEND = 0.30


def _load(rel_path: str) -> "pygame.Surface | None":
    path = os.path.join(ASSETS_DIR, rel_path)
    if not os.path.exists(path):
        return None
    return pygame.image.load(path).convert_alpha()


def _load_bot_sprite(bot_type: str) -> "pygame.Surface | None":
    return _load(os.path.join("bots", f"bot_{bot_type.lower()}.png"))


def _load_fx(prefix: str) -> list["pygame.Surface"]:
    """Load fx frame sequences (assets/fx/fx_<prefix>_NN.png)."""
    frames = []
    for i in range(12):
        surf = _load(os.path.join("fx", f"fx_{prefix}_{i:02d}.png"))
        if surf is None:
            break
        frames.append(surf)
    return frames


class PlaybackViewer:
    def __init__(self, screen_size: tuple[int, int], replay_path: str | None = None):
        """`replay_path=None` opens the match workspace empty: nothing is
        auto-simulated and nothing is auto-picked — the user chooses a map
        and strategies (restored from their last session when available)
        and presses Run Match."""
        self.screen_size = screen_size

        self.bot_sprites: dict[str, "pygame.Surface | None"] = {}

        # Same tile/marker textures the map editor uses (map_canvas_renderer.py)
        # and the Godot original's map_renderer.gd used — this viewer used to
        # draw flat DENSITY_COLOR rects and procedural circles instead of any
        # of the real art, even though it was sitting right here in assets/.
        self.terrain_textures = {
            Density.LOW: _load("tiles/tile_low.png"),
            Density.MEDIUM: _load("tiles/tile_medium.png"),
            Density.HIGH: _load("tiles/tile_high.png"),
            Density.BONE: _load("tiles/tile_bone.png"),
        }
        self.stream_h_texture = _load("tiles/tile_stream_h.png")
        self.stream_v_texture = _load("tiles/tile_stream_v.png")
        self.habitas_neutral_texture = _load("markers/habitas_neutral.png")
        self.habitas_owned_texture = _load("markers/habitas_owned.png")
        self.azn_texture = _load("markers/azn_node.png")
        self._scaled_cache: dict[tuple, "pygame.Surface"] = {}
        self._owned_tint_cache: dict[tuple, "pygame.Surface"] = {}

        # Event VFX (VIS-08): short animated effects drawn over the cell an
        # event happened in, so a spectator can see *why* the state changed.
        # They loop while the frame is current — informative even paused.
        self.fx = {
            "attack": _load_fx("attack"),
            "destruct": _load_fx("destruct"),
            "collect": _load_fx("azn_collect"),
            "built": _load_fx("bot_built"),
        }
        self._fx_clock = 0.0

        # Seed control (UX-04): Restart rolls a fresh random seed unless
        # locked, and the seed in use is always shown — an exact rerun is
        # one lock-click away instead of impossible.
        self.match_seed: int | None = None
        self.seed_locked = False

        self.playing = False
        self.speed_index = 2  # 1.0x
        self._accum = 0.0

        # Placeholder until _load_replay() fits the whole map into the
        # canvas (_fit_view); wheel zoom then goes up to MAX_ZOOM, where a
        # bot sprite is comfortably readable.
        self.zoom = 1.5
        self.scroll_x = 0
        self.scroll_y = 0
        self.selected_bot_id: int | None = None
        self._left_down_pos: tuple[int, int] | None = None
        self._left_dragged = False

        self.on_back_to_menu = None  # callback()

        self.picker = FilePickerModal()
        self.running_match = False
        self._match_thread: threading.Thread | None = None
        self._match_result: dict | None = None
        self._match_started_at = 0.0
        self.match_message = ""

        self.canvas_rect = pygame.Rect(0, CONTROL_BAR_HEIGHT, 0, 0)
        self._recompute_canvas_rect()

        self.browser = FileBrowserModal()

        self.log: MatchLog | None = None
        self.map: MapData | None = None
        self.current_frame = 0
        if replay_path is not None:
            self._load_replay(replay_path)
        else:
            self._index_replay()

        # What the picker buttons show and what Run/Restart will use.
        # Restored from the last session's choices (user_prefs) — never
        # auto-filled with "first file in some folder": an unset slot
        # stays visibly unset until the user picks.
        self.selected_map: str | None = user_prefs.existing_file("last_map")
        last = user_prefs.existing_files("last_strategies")
        self.selected_p0: str | None = last[0] if len(last) > 0 else None
        self.selected_p1: str | None = last[1] if len(last) > 1 else None
        if self.log is not None:
            self._init_selection_from_log()

        self._build_controls()

    def _init_selection_from_log(self) -> None:
        """Point the selectors at whatever produced the loaded replay, so
        they describe what's on screen — but only where those files still
        exist; missing ones keep the current (prefs-restored) selection
        rather than being auto-filled from a folder listing."""
        strategies = list(self.log.player_strategies) if self.log else []
        if len(strategies) > 0 and os.path.exists(strategies[0]):
            self.selected_p0 = strategies[0]
        if len(strategies) > 1 and os.path.exists(strategies[1]):
            self.selected_p1 = strategies[1]
        map_path = self._resolve_map_path(self.log.map_name) if self.log else None
        if map_path is not None:
            self.selected_map = map_path

    def _load_replay(self, replay_path: str) -> None:
        self.log = MatchLog.load_from_file(replay_path)
        self.map = None
        if self.log is not None:
            map_path = self._resolve_map_path(self.log.map_name)
            self.map = load_from_file(map_path) if map_path else None
        if self.map is None:
            self.map = MapData(40, 40)  # fallback blank map so the viewer doesn't crash
        self.current_frame = 0
        self.selected_bot_id = None
        self._accum = 0.0
        self._index_replay()
        # Replays now record their seed (match_log.py) — show it for any
        # loaded replay, not only matches this screen launched itself.
        if self.log is not None and self.log.seed is not None:
            self.match_seed = self.log.seed
        self._fit_view()
        # Start rolling immediately: every path into a freshly loaded replay
        # (first match from the menu, Restart, Replays...) means "watch
        # this" — landing paused on turn 0 made each one a two-click job.
        self._set_playing(True)

    def _set_playing(self, playing: bool) -> None:
        self.playing = playing
        if hasattr(self, "btn_play"):
            self.btn_play.icon = icons.pause_icon(22) if playing else icons.play_icon(22)

    def _fit_view(self) -> None:
        """Zoom/center so the whole map is visible — the previous fixed
        1.5x default cropped every map bigger than ~48 cells and started
        on the top-left corner, so the far player's spawn began off-screen."""
        if self.map is None or self.canvas_rect.width <= 0 or self.canvas_rect.height <= 0:
            return
        map_w = self.map.width * CELL_SIZE
        map_h = self.map.height * CELL_SIZE
        fit = min(self.canvas_rect.width / map_w, self.canvas_rect.height / map_h)
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, fit))
        self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        """Keep the map on screen: pan freedom only in the axis where the
        map overflows the canvas, centered in the axis where it doesn't —
        before this, panning could push the map fully off-screen with no
        landmark to find the way back."""
        size = CELL_SIZE * self.zoom
        map_w = int(self.map.width * size) if self.map else 0
        map_h = int(self.map.height * size) if self.map else 0
        for attr, map_px, canvas_px in (("scroll_x", map_w, self.canvas_rect.width),
                                        ("scroll_y", map_h, self.canvas_rect.height)):
            if map_px <= canvas_px:
                setattr(self, attr, -(canvas_px - map_px) // 2)
            else:
                setattr(self, attr, max(0, min(getattr(self, attr), map_px - canvas_px)))

    def _index_replay(self) -> None:
        """Precompute id -> (owner, type) and the notable-event timeline
        used by the HUD ticker, in one pass over the frames."""
        self._bot_meta: dict[int, tuple[int, str]] = {}
        self._timeline: list[tuple[int, str]] = []
        self._has_hazards = False
        if self.log is None:
            return
        for f in self.log.frames:
            if f.get("hazards"):
                self._has_hazards = True
            for b in f["bots"]:
                if b["id"] not in self._bot_meta:
                    self._bot_meta[b["id"]] = (b["owner"], b["type"])
            for e in f.get("events", []):
                text = self._event_text(e)
                if text:
                    self._timeline.append((f["turn"], text))

    def _event_text(self, e: dict) -> str | None:
        t = e.get("type")
        if t == "bot_built":
            owner, typ = self._bot_meta.get(e["new_bot"], (None, e.get("type_name", "?")))
            return f"P{owner + 1} built {e.get('type_name', typ)}" if owner is not None else None
        if t == "bot_destroyed":
            owner, typ = self._bot_meta.get(e["bot_id"], (e.get("owner"), "bot"))
            cause = {"attack": "shot down", "hazard": "killed by white cell"}.get(e.get("by"), "destroyed")
            return f"P{owner + 1} {typ} {cause}"
        if t in ("auto_destruct", "self_destruct"):
            owner, typ = self._bot_meta.get(e["bot_id"], (None, "bot"))
            if owner is None:
                return None
            return f"P{owner + 1} {typ} expired" if t == "auto_destruct" else f"P{owner + 1} {typ} self-destructed"
        if t == "hazard_destroyed":
            return "White cell destroyed"
        if t == "injection_point_created":
            return f"P{e['player'] + 1} opened injection point"
        return None

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
        self._clamp_scroll()

    def _recompute_canvas_rect(self) -> None:
        w = self.screen_size[0] - SIDEBAR_WIDTH
        h = self.screen_size[1] - CONTROL_BAR_HEIGHT
        self.canvas_rect = pygame.Rect(0, CONTROL_BAR_HEIGHT, max(0, w), max(0, h))

    def _build_controls(self) -> None:
        y = 9
        size = 32
        # Icon reflects the current playing state — _build_controls also
        # runs on resize and after auto-playing loads, not just at startup.
        play_icon = icons.pause_icon(22) if self.playing else icons.play_icon(22)
        self.btn_play = Button((10, y, size, size), "", icon=play_icon, on_click=self._toggle_play)
        x = 10 + size + 6
        self.btn_step_back = Button((x, y, size, size), "", icon=icons.step_back_icon(22), on_click=lambda: self._step(-1))
        x += size + 4
        self.btn_step_fwd = Button((x, y, size, size), "", icon=icons.step_forward_icon(22), on_click=lambda: self._step(1))
        x += size + 14
        self.btn_speed_down = Button((x, y, size, size), "", icon=icons.speed_down_icon(22), on_click=lambda: self._change_speed(-1))
        x += size + 50  # leaves room for the "1.0x" label drawn between the buttons
        self.btn_speed_up = Button((x, y, size, size), "", icon=icons.speed_up_icon(22), on_click=lambda: self._change_speed(1))
        self.btn_back = Button((self.screen_size[0] - 130, y, 120, size), "Back to Menu",
                                icon=icons.back_arrow_icon(16), on_click=self._back)

        # Row 2 — change what's being watched and re-run, without leaving
        # this screen. Mirrors the main menu's picker pattern exactly.
        y2 = TOP_ROW_HEIGHT + 4
        sel_h = 32
        self.btn_select_map = Button((10, y2, 170, sel_h), "", on_click=self._open_map_picker)
        x2 = 10 + 170 + 6
        self.btn_select_p0 = Button((x2, y2, 230, sel_h), "", on_click=lambda: self._open_strategy_picker("p0"))
        x2 += 230 + 6
        self.btn_select_p1 = Button((x2, y2, 230, sel_h), "", on_click=lambda: self._open_strategy_picker("p1"))
        x2 += 230 + 14
        self.btn_restart = Button((x2, y2, 100, sel_h), "Restart", icon=icons.play_icon(14), on_click=self._restart_match)
        x2 += 100 + 8
        self.btn_load_replay = Button((x2, y2, 96, sel_h), "Replays...", on_click=self._open_replay_picker,
                                       tooltip="Open any saved replay (tournament and headless runs included)")
        x2 += 96 + 8
        self.btn_seed_lock = Button((x2, y2, 118, sel_h), "", toggle=True, on_click=self._toggle_seed_lock,
                                     tooltip="Locked: Restart reruns the exact same match. Unlocked: new random seed each time.")
        self._refresh_seed_label()
        self._refresh_selector_labels()

        self._compute_hud_layout()
        sidebar_x = self.screen_size[0] - SIDEBAR_WIDTH
        max_frame = len(self.log.frames) - 1 if self.log and self.log.frames else 0
        self.turn_slider = Slider((sidebar_x + 12, self._hud_layout["slider"], SIDEBAR_WIDTH - 24, 20),
                                   0, max_frame, self.current_frame, on_change=self._jump_to)

        self.controls = [self.btn_play, self.btn_step_back, self.btn_step_fwd,
                          self.btn_speed_down, self.btn_speed_up, self.btn_back, self.turn_slider,
                          self.btn_select_map, self.btn_select_p0, self.btn_select_p1, self.btn_restart,
                          self.btn_load_replay, self.btn_seed_lock]

    def _refresh_selector_labels(self) -> None:
        def name(path: str | None, empty: str) -> str:
            return os.path.basename(path).rsplit(".", 1)[0] if path else empty
        self.btn_select_map.text = f"Map: {name(self.selected_map, '(pick a map)')}"
        self.btn_select_p0.text = f"P1: {name(self.selected_p0, '(pick strategy)')}"
        self.btn_select_p1.text = f"P2: {name(self.selected_p1, '(pick strategy)')}"
        self.btn_restart.text = "Restart" if self.log is not None else "Run Match"

    def _open_map_picker(self) -> None:
        # Browses the whole filesystem, starting where the user last
        # picked a map (maps/ only as the first-run default) — map files
        # aren't confined to the project folder.
        start = user_prefs.existing_dir("last_map_dir", os.path.abspath(MAPS_DIR))
        self.browser.open("Select map (.json)", start, (".json",),
                          lambda paths: self._apply_picker_choice("map", paths[0]))

    def _open_strategy_picker(self, slot: str) -> None:
        start = user_prefs.existing_dir("last_strategy_dir", os.path.abspath(STRATEGIES_DIR))
        label = "Player 1" if slot == "p0" else "Player 2"
        self.browser.open(f"Select {label} strategy (.py)", start, (".py",),
                          lambda paths: self._apply_picker_choice(slot, paths[0]))

    def _apply_picker_choice(self, slot: str, path: str) -> None:
        if slot == "map":
            self.selected_map = path
            user_prefs.update(last_map_dir=os.path.dirname(path))
        elif slot == "p0":
            self.selected_p0 = path
            user_prefs.update(last_strategy_dir=os.path.dirname(path))
        elif slot == "p1":
            self.selected_p1 = path
            user_prefs.update(last_strategy_dir=os.path.dirname(path))
        self._refresh_selector_labels()

    def _toggle_seed_lock(self) -> None:
        self.seed_locked = self.btn_seed_lock.pressed
        self._refresh_seed_label()

    def _refresh_seed_label(self) -> None:
        seed_text = "—" if self.match_seed is None else str(self.match_seed)
        self.btn_seed_lock.text = f"Seed {seed_text} {'●' if self.seed_locked else '○'}"
        self.btn_seed_lock.pressed = self.seed_locked

    def _open_replay_picker(self) -> None:
        files = sorted(glob.glob(os.path.join(REPLAYS_DIR, "*.json")),
                        key=os.path.getmtime, reverse=True)
        files = [f for f in files if not f.endswith("tournament_results.json")]
        if not files:
            self.match_message = "No replays found in replays/"
            return
        files = files[:14]
        labels = [f"{os.path.basename(f)}   ({self._age_label(os.path.getmtime(f))})" for f in files]
        self.picker.open("Open replay (newest first)", files, self._load_picked_replay, labels=labels)

    @staticmethod
    def _age_label(mtime: float) -> str:
        age = max(0, time.time() - mtime)
        if age < 90:
            return "just now"
        if age < 3600:
            return f"{int(age // 60)} min ago"
        if age < 86400:
            return f"{int(age // 3600)} h ago"
        return f"{int(age // 86400)} d ago"

    def _load_picked_replay(self, path: str) -> None:
        self._load_replay(path)
        self._init_selection_from_log()
        self._refresh_selector_labels()
        self._refresh_seed_label()
        max_frame = len(self.log.frames) - 1 if self.log and self.log.frames else 0
        self.turn_slider.set_range(0, max_frame)
        self.turn_slider.set_value(0)
        self._compute_hud_layout()
        self.match_message = f"Loaded {os.path.basename(path)}"

    def _restart_match(self) -> None:
        if self.running_match:
            return
        missing = [p for p in (self.selected_map, self.selected_p0, self.selected_p1)
                   if p is None or not os.path.exists(p)]
        if missing:
            self.match_message = "Pick a map and both strategies first (buttons above)"
            return

        # Remember what's being run, so the next app start restores it.
        user_prefs.update(last_map=self.selected_map,
                          last_strategies=[self.selected_p0, self.selected_p1])

        if not (self.seed_locked and self.match_seed is not None):
            self.match_seed = random.randrange(1_000_000)
        self._refresh_seed_label()

        self.running_match = True
        self.match_message = ""
        self._match_result = None
        self._match_started_at = time.monotonic()
        self._match_thread = threading.Thread(
            target=self._match_worker,
            args=(self.selected_map, [self.selected_p0, self.selected_p1], self.match_seed),
            daemon=True)
        self._match_thread.start()

    def _match_worker(self, map_path: str, strategy_paths: list[str], seed: int) -> None:
        try:
            map_data = load_from_file(map_path)
            if map_data is None:
                # Reachable now that the picker browses anywhere: any
                # .json can be chosen, not just files from maps/.
                self._match_result = {"error": f"Not a valid map file: {os.path.basename(map_path)}"}
                return
            sim = SimulationCore(map_data, strategy_paths, seed=seed)
            log = sim.run()

            os.makedirs(REPLAYS_DIR, exist_ok=True)
            out_path = os.path.join(REPLAYS_DIR, "last_match.json")
            if not log.save_to_file(out_path):
                self._match_result = {"error": f"Match ran but failed to save replay to {out_path}"}
                return

            a, b = (os.path.basename(p) for p in strategy_paths)
            self._match_result = {
                "path": out_path,
                "summary": f"{a} vs {b}: complete in {log.total_turns} turns — winner: Player {log.winner_id + 1}",
            }
        except Exception as e:
            self._match_result = {"error": f"Match failed: {e}"}

    def _compute_hud_layout(self) -> None:
        # Every HUD section's y-position computed once here, rather than by
        # hand inside _draw_hud — the map editor sidebar had the same
        # hand-computed-offsets-drift-out-of-sync risk earlier in this
        # project's history, fixed there the same way.
        num_rows = len(self.log.player_strategies) if self.log else 0
        y = CONTROL_BAR_HEIGHT + 12
        layout = {"map_info": y}
        y += 22
        layout["turn"] = y
        y += 22
        layout["slider"] = y
        y += 26
        layout["scores_header"] = y
        y += 20
        layout["score_rows"] = y
        y += num_rows * 20
        layout["winner"] = y  # reserved unconditionally so the legend below never shifts
        y += 22
        layout["legend_header"] = y
        y += 20
        layout["legend_rows"] = y
        legend_rows = 7 + (1 if getattr(self, "_has_hazards", False) else 0)
        y += legend_rows * 16 + 10
        layout["ticker_header"] = y
        y += 20
        layout["ticker_rows"] = y
        self._hud_layout = layout

    def _jump_to(self, frame_index: int) -> None:
        # Matches playback_scene.gd's jump_to: relocate and reset the
        # per-frame accumulator, but don't touch self.playing — scrubbing
        # the slider while playing keeps playing from the new position,
        # scrubbing while paused stays paused.
        if self.log is None or not self.log.frames:
            return
        self.current_frame = max(0, min(len(self.log.frames) - 1, frame_index))
        self._accum = 0.0

    def _back(self) -> None:
        if self.on_back_to_menu:
            self.on_back_to_menu()

    def _toggle_play(self) -> None:
        self._set_playing(not self.playing)

    def _step(self, delta: int) -> None:
        if self.log is None:
            return
        self.current_frame = max(0, min(len(self.log.frames) - 1, self.current_frame + delta))

    def _change_speed(self, delta: int) -> None:
        self.speed_index = max(0, min(len(SPEEDS) - 1, self.speed_index + delta))

    # --- update / events ---

    def update(self, dt: float) -> None:
        self._fx_clock += dt
        if self.running_match:
            if self._match_thread is not None and not self._match_thread.is_alive():
                self.running_match = False
                result = self._match_result or {}
                if "error" in result:
                    self.match_message = result["error"]
                else:
                    self.match_message = result["summary"]
                    self._load_replay(result["path"])
                    max_frame = len(self.log.frames) - 1 if self.log and self.log.frames else 0
                    self.turn_slider.set_range(0, max_frame)
                    self.turn_slider.set_value(0)
                    self._compute_hud_layout()
                    self._refresh_selector_labels()  # "Run Match" -> "Restart" after the first run
            return

        if not self.playing or self.log is None or not self.log.frames:
            return
        self._accum += dt * SPEEDS[self.speed_index]
        turns_per_second = 8.0
        while self._accum >= 1.0 / turns_per_second:
            self._accum -= 1.0 / turns_per_second
            if self.current_frame < len(self.log.frames) - 1:
                self.current_frame += 1
            else:
                self._set_playing(False)
                break

    def handle_event(self, event: "pygame.event.Event") -> None:
        if self.browser.handle_event(event):
            return
        if self.picker.handle_event(event):
            return
        if self.running_match:
            return  # nothing meaningful to interact with while a new match computes

        for btn in self.controls:
            if btn.handle_event(event):
                return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.canvas_rect.collidepoint((mx, my)):
                # Anchored at the cursor: the world point under the mouse
                # stays under the mouse, so zooming in on a fight actually
                # lands on the fight instead of drifting toward (0,0).
                # Multiplicative steps feel even across the zoom range
                # (the old flat +0.1 was glacial at 6x and coarse at 0.5x).
                old = self.zoom
                self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, old * (1.15 ** event.y)))
                if self.zoom != old:
                    wx = (mx - self.canvas_rect.x + self.scroll_x) / old
                    wy = (my - self.canvas_rect.y + self.scroll_y) / old
                    self.scroll_x = int(wx * self.zoom - (mx - self.canvas_rect.x))
                    self.scroll_y = int(wy * self.zoom - (my - self.canvas_rect.y))
                    self._clamp_scroll()
            return

        # Left button: click-to-select a bot, or drag-to-pan if the mouse
        # actually moves before release — distinguished by whether any
        # motion happened between down and up, not by which button it is.
        # Middle-drag (below) still works too for anyone used to it, but
        # requires a middle mouse button many trackpads/mice don't have a
        # comfortable way to hold — left-drag needs nothing special.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.canvas_rect.collidepoint(event.pos):
            self._left_down_pos = event.pos
            self._left_dragged = False
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._left_down_pos is not None and not self._left_dragged \
                    and self.canvas_rect.collidepoint(event.pos):
                self._handle_canvas_click(event.pos)
            self._left_down_pos = None
            self._left_dragged = False
            return
        if event.type == pygame.MOUSEMOTION and event.buttons[0] and self._left_down_pos is not None:
            self._left_dragged = True
            self.scroll_x -= event.rel[0]
            self.scroll_y -= event.rel[1]
            self._clamp_scroll()
            return
        if event.type == pygame.MOUSEMOTION and event.buttons[1]:
            self.scroll_x -= event.rel[0]
            self.scroll_y -= event.rel[1]
            self._clamp_scroll()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._toggle_play()
            elif event.key == pygame.K_LEFT:
                self._step(-1)
            elif event.key == pygame.K_RIGHT:
                self._step(1)
            elif event.key == pygame.K_HOME:
                self._jump_to(0)
            elif event.key == pygame.K_END and self.log and self.log.frames:
                self._jump_to(len(self.log.frames) - 1)
            elif event.key == pygame.K_f:
                self._fit_view()

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
        pygame.draw.line(surface, (12, 12, 16), (0, TOP_ROW_HEIGHT), (self.screen_size[0], TOP_ROW_HEIGHT), 1)
        for btn in self.controls:
            btn.enabled = not self.running_match
            if btn is self.turn_slider and (self.log is None or not self.log.frames):
                continue  # nothing to scrub yet — a lone handle floating in the empty HUD reads as a glitch
            btn.draw(surface)
        speed_label = f"{SPEEDS[self.speed_index]}x"
        # Positioned relative to the actual button rects, not hardcoded
        # coordinates that would silently drift out of sync the next time
        # the buttons either side of it move (the same bug class fixed in
        # the map editor sidebar's header labels).
        label_center_x = (self.btn_speed_down.rect.right + self.btn_speed_up.rect.left) // 2
        font = get_font(14)
        label_surf = font.render(speed_label, True, (215, 218, 228))
        surface.blit(label_surf, (label_center_x - label_surf.get_width() // 2, self.btn_speed_down.rect.y + 8))

        # Keyboard-shortcut hint in row 1's dead space, only when it fits
        # between the speed controls and Back — the shortcuts were
        # completely undiscoverable before (nothing on screen mentioned
        # them and Button tooltips weren't rendered on this screen either).
        hint_font = get_font(11)
        hint_surf = hint_font.render(KEY_HINT, True, (130, 134, 148))
        hint_x = self.btn_speed_up.rect.right + 28
        if hint_x + hint_surf.get_width() <= self.btn_back.rect.left - 16:
            surface.blit(hint_surf, (hint_x, self.btn_speed_down.rect.y + 9))

        if self.log is None or not self.log.frames:
            # Empty workspace (nothing auto-runs anymore): say what to do
            # next instead of the old "No replay loaded" error tone.
            cx = 24
            cy = CONTROL_BAR_HEIGHT + 36
            draw_text(surface, "No match yet.", (cx, cy), size=18, color=(220, 222, 230))
            draw_text(surface, "Pick a map and both strategies with the buttons above, then press Run Match.",
                      (cx, cy + 30), size=13, color=(170, 174, 188))
            draw_text(surface, "Or open a previous match with Replays...",
                      (cx, cy + 52), size=13, color=(170, 174, 188))
            self._draw_status_strip(surface)
            draw_hover_tooltips(surface, [b for b in self.controls if isinstance(b, Button)])
            self.picker.draw(surface, self.screen_size)
            self.browser.draw(surface, self.screen_size)
            return

        frame = self.log.frames[self.current_frame]

        prev_clip = surface.get_clip()
        surface.set_clip(self.canvas_rect)
        self._draw_map(surface)
        self._draw_habitas(surface, frame)
        self._draw_azn(surface, frame)
        self._draw_hazards_frame(surface, frame)
        self._draw_bots(surface, frame)
        self._draw_effects(surface, frame)
        surface.set_clip(prev_clip)

        # Keep the slider's handle in sync regardless of what moved
        # current_frame (play/step/speed all bypass _jump_to).
        self.turn_slider.set_value(self.current_frame)
        self._draw_hud(surface, frame)
        self._draw_inspector(surface, frame)
        self._draw_status_strip(surface)
        draw_hover_tooltips(surface, [b for b in self.controls if isinstance(b, Button)])

        self.picker.draw(surface, self.screen_size)
        self.browser.draw(surface, self.screen_size)

    def _draw_status_strip(self, surface: "pygame.Surface") -> None:
        """Match status (running spinner / last result) on its own
        full-width strip at the top of the canvas. It used to be drawn
        at btn_restart.rect.right — right on top of the Replays.../Seed
        buttons added next to Restart in v0.0.14 (verified by screenshot:
        both the message and the button labels were unreadable)."""
        if not (self.running_match or self.match_message):
            return
        strip = pygame.Rect(0, CONTROL_BAR_HEIGHT, max(self.canvas_rect.width, 320), 24)
        overlay = pygame.Surface(strip.size, pygame.SRCALPHA)
        overlay.fill((14, 14, 18, 225))
        surface.blit(overlay, strip.topleft)
        if self.running_match:
            elapsed = time.monotonic() - self._match_started_at
            cx, cy, radius = 16, strip.centery, 7
            angle = (elapsed * 4.0) % (2 * math.pi)
            for i in range(8):
                a = angle + i * (2 * math.pi / 8)
                shade = 80 + int(150 * (i / 8))
                pygame.draw.circle(surface, (shade, shade, shade),
                                   (int(cx + radius * math.cos(a)), int(cy + radius * math.sin(a))), 2)
            draw_text(surface, f"Simulating... {elapsed:.1f}s", (cx + 16, strip.y + 5), size=12, color=(220, 200, 120))
        else:
            draw_text(surface, self.match_message, (12, strip.y + 5), size=12, color=(220, 200, 120))

    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        size = CELL_SIZE * self.zoom
        sx = self.canvas_rect.x + x * size - self.scroll_x
        sy = self.canvas_rect.y + y * size - self.scroll_y
        return pygame.Rect(int(sx), int(sy), int(size) + 1, int(size) + 1)

    def _scaled(self, tex: "pygame.Surface", size: int) -> "pygame.Surface":
        key = (id(tex), size)
        cached = self._scaled_cache.get(key)
        if cached is None or cached.get_width() != size:
            cached = pygame.transform.smoothscale(tex, (size, size))
            self._scaled_cache[key] = cached
        return cached

    def _owned_tinted(self, size: int, tint: tuple[int, int, int]) -> "pygame.Surface | None":
        if self.habitas_owned_texture is None:
            return None
        key = (size, tint)
        cached = self._owned_tint_cache.get(key)
        if cached is not None:
            return cached
        tinted = self._scaled(self.habitas_owned_texture, size).copy()
        tinted.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._owned_tint_cache[key] = tinted
        return tinted

    def _draw_map(self, surface: "pygame.Surface") -> None:
        # Grid lines go on a separate SRCALPHA overlay blitted once at the
        # end — pygame.draw.rect ignores alpha on the main (non-alpha)
        # surface and would draw GRID_COLOR fully opaque otherwise.
        grid_overlay = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)

        for y in range(self.map.height):
            for x in range(self.map.width):
                cell = self.map._cells[y * self.map.width + x]
                r = self._cell_rect(x, y)
                if r.right < self.canvas_rect.left or r.left > self.canvas_rect.right:
                    continue
                if r.bottom < self.canvas_rect.top or r.top > self.canvas_rect.bottom:
                    continue

                if cell["stream_dir"] == StreamDir.NONE:
                    tex = self.terrain_textures.get(cell["density"])
                    if tex:
                        surface.blit(self._scaled(tex, r.width), r.topleft)
                    else:
                        pygame.draw.rect(surface, DENSITY_COLOR[cell["density"]], r)
                else:
                    self._draw_stream_cell(surface, r, cell["stream_dir"])

                overlay_r = pygame.Rect(r.x - self.canvas_rect.x, r.y - self.canvas_rect.y, r.width, r.height)
                pygame.draw.rect(grid_overlay, GRID_COLOR, overlay_r, width=1)

        surface.blit(grid_overlay, self.canvas_rect.topleft)

    def _draw_stream_cell(self, surface, r: pygame.Rect, direction: StreamDir) -> None:
        # Same texture + flip logic as the map editor's
        # MapCanvasRenderer._draw_stream_cell, and the same two-step
        # "biological texture, then a crisp procedural arrow on top" as
        # the Godot original's map_renderer.gd — the arrow alone (the old
        # behavior here) skipped the actual stream art entirely.
        if direction in (StreamDir.EAST, StreamDir.WEST):
            tex = self.stream_h_texture
            if tex:
                scaled = self._scaled(tex, r.width)
                if direction == StreamDir.WEST:
                    scaled = pygame.transform.flip(scaled, True, False)
                surface.blit(scaled, r.topleft)
            else:
                pygame.draw.rect(surface, (102, 51, 51), r)
        else:
            tex = self.stream_v_texture
            if tex:
                scaled = self._scaled(tex, r.width)
                if direction == StreamDir.NORTH:
                    scaled = pygame.transform.flip(scaled, False, True)
                surface.blit(scaled, r.topleft)
            else:
                pygame.draw.rect(surface, (102, 51, 51), r)

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
        # Same texture choice as map_renderer.gd: the neutral marker for an
        # unclaimed point, or the owned marker tinted toward the owning
        # player's color (habitas_owned.png is a near-white base texture
        # specifically designed for this multiply-tint, unlike the bot
        # sprites' own multi-color art).
        for hp in frame["habitas_points"]:
            r = self._cell_rect(hp["pos"][0], hp["pos"][1])
            owner = hp["owner"]
            if owner >= 0:
                base = PLAYER_COLORS[owner % len(PLAYER_COLORS)]
                tint = tuple(int(c + (255 - c) * OWNED_BLEND) for c in base)
                tex = self._owned_tinted(r.width, tint)
            else:
                tex = self._scaled(self.habitas_neutral_texture, r.width) if self.habitas_neutral_texture else None
            if tex:
                surface.blit(tex, r.topleft)
            else:
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
            if self.azn_texture:
                surface.blit(self._scaled(self.azn_texture, r.width), r.topleft)
            else:
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
                # Shrink the icon just enough that the team ring isn't drawn
                # over it — a bigger inset than this made the sprite shrink
                # to a handful of pixels at the default zoom and become an
                # indistinct blob rather than a recognizable bot type.
                inset = max(1, r.width // 10)
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

    def _draw_hazards_frame(self, surface: "pygame.Surface", frame: dict) -> None:
        """White cells: pale pulsing blobs with a nucleus — drawn
        procedurally (no sprite asset exists for them) but sized and
        animated so they read as alive, hostile tissue."""
        for h in frame.get("hazards", []):
            if not h.get("alive", True):
                continue
            r = self._cell_rect(h["pos"][0], h["pos"][1])
            pulse = 1.0 + 0.10 * math.sin(self._fx_clock * 4.0 + h["id"] * 1.7)
            radius = int(r.width * 0.48 * pulse)
            center = r.center
            body = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(body, (238, 240, 248, 215), (radius * 2, radius * 2), radius)
            pygame.draw.circle(body, (205, 210, 232, 235), (radius * 2, radius * 2), int(radius * 0.55))
            pygame.draw.circle(body, (160, 168, 205, 255), (radius * 2, radius * 2), int(radius * 0.25))
            surface.blit(body, (center[0] - radius * 2, center[1] - radius * 2))

    def _fx_frame(self, kind: str) -> "pygame.Surface | None":
        frames = self.fx.get(kind) or []
        if not frames:
            return None
        return frames[int(self._fx_clock * 10) % len(frames)]

    def _draw_effects(self, surface: "pygame.Surface", frame: dict) -> None:
        """Overlay this turn's events where they happened: attack tracers,
        impact/build/collect/destruct animations. Loops while the frame is
        current, so stepping through turns shows exactly what changed."""
        bot_pos = {b["id"]: tuple(b["pos"]) for b in frame["bots"]}
        hazard_pos = {h["id"]: tuple(h["pos"]) for h in frame.get("hazards", [])}
        size = int(CELL_SIZE * self.zoom * 1.7)

        def blit_fx(kind: str, cell: tuple[int, int]) -> None:
            img = self._fx_frame(kind)
            if img is None:
                return
            r = self._cell_rect(cell[0], cell[1])
            scaled = pygame.transform.smoothscale(img, (size, size))
            surface.blit(scaled, (r.centerx - size // 2, r.centery - size // 2))

        def tracer(src: tuple[int, int] | None, dst: tuple[int, int],
                    color: tuple[int, int, int], width: int = 2) -> None:
            if src is None:
                return
            a = self._cell_rect(src[0], src[1]).center
            b = self._cell_rect(dst[0], dst[1]).center
            pygame.draw.line(surface, color, a, b, width)

        for e in frame.get("events", []):
            t = e.get("type")
            if t == "attack":
                at = tuple(e.get("at", (0, 0)))
                tracer(bot_pos.get(e.get("attacker")), at, (255, 235, 130))
                blit_fx("attack", at)
            elif t == "attack_blocked":
                at = tuple(e.get("at", (0, 0)))
                tracer(bot_pos.get(e.get("attacker")), at, (120, 120, 130), 1)
            elif t == "hazard_attack":
                at = tuple(e.get("at", (0, 0)))
                tracer(hazard_pos.get(e.get("hazard")), at, (235, 238, 250))
                blit_fx("attack", at)
            elif t == "bot_built":
                pos = bot_pos.get(e.get("new_bot"))
                if pos:
                    blit_fx("built", pos)
            elif t == "azn_collected":
                node = e.get("node")
                if node:
                    blit_fx("collect", tuple(node))
            elif t in ("bot_destroyed", "hazard_destroyed"):
                at = e.get("at")
                if at:
                    blit_fx("destruct", tuple(at))
            elif t in ("auto_destruct", "self_destruct"):
                pos = bot_pos.get(e.get("bot_id"))
                if pos:
                    blit_fx("destruct", pos)

    # Same legend the Godot HUD shows (hud.gd's legend_entries) — texture
    # + label pairs, reusing the textures already loaded for the canvas
    # itself rather than loading separate copies.
    def _legend_entries(self) -> list[tuple["pygame.Surface | None", str]]:
        return [
            (self.terrain_textures.get(Density.LOW), "Low density (2 turns)"),
            (self.terrain_textures.get(Density.MEDIUM), "Medium density (3 turns)"),
            (self.terrain_textures.get(Density.HIGH), "High density (4 turns)"),
            (self.terrain_textures.get(Density.BONE), "Bone (impassable)"),
            (self.stream_h_texture, "Bloodstream"),
            (self.habitas_neutral_texture, "Habitas Point"),
            (self.azn_texture, "AZN Node"),
        ]

    def _draw_hud(self, surface: "pygame.Surface", frame: dict) -> None:
        x = self.screen_size[0] - SIDEBAR_WIDTH
        rect = pygame.Rect(x, CONTROL_BAR_HEIGHT, SIDEBAR_WIDTH, self.screen_size[1] - CONTROL_BAR_HEIGHT)
        pygame.draw.rect(surface, (32, 32, 38), rect)
        pygame.draw.line(surface, (12, 12, 16), (x, CONTROL_BAR_HEIGHT), (x, self.screen_size[1]), 2)

        L = self._hud_layout
        draw_text(surface, f"Map: {self.log.map_name}", (x + 12, L["map_info"]), size=12, color=(160, 165, 180))
        draw_text(surface, f"Turn {frame['turn']} / {self.log.total_turns}", (x + 12, L["turn"]), size=15, color=(235, 235, 235))

        self.turn_slider.draw(surface)

        draw_text(surface, "Scores", (x + 12, L["scores_header"]), size=12, color=(160, 165, 180))
        y = L["score_rows"]
        for pid_str, score in sorted(frame["scores"].items(), key=lambda kv: int(kv[0])):
            pid = int(pid_str)
            color = PLAYER_COLORS[pid % len(PLAYER_COLORS)]
            alive = sum(1 for b in frame["bots"] if b["owner"] == pid and b["alive"])
            pygame.draw.rect(surface, color, (x + 12, y + 2, 10, 10))
            draw_text(surface, f"Player {pid + 1}: {score} pts  ({alive} bots alive)", (x + 28, y), size=12)
            y += 20

        if self.current_frame == len(self.log.frames) - 1:
            draw_text(surface, f"Winner: Player {self.log.winner_id + 1}", (x + 12, L["winner"]), size=14, color=(120, 230, 140))

        draw_text(surface, "Map Legend", (x + 12, L["legend_header"]), size=12, color=(160, 165, 180))
        y = L["legend_rows"]
        for tex, label in self._legend_entries():
            if tex:
                surface.blit(self._scaled(tex, 12), (x + 12, y + 1))
            draw_text(surface, label, (x + 30, y), size=10, color=(185, 188, 196))
            y += 16
        if self._has_hazards:
            pygame.draw.circle(surface, (238, 240, 248), (x + 18, y + 7), 6)
            pygame.draw.circle(surface, (160, 168, 205), (x + 18, y + 7), 3)
            draw_text(surface, "White cell (attacks all bots)", (x + 30, y), size=10, color=(185, 188, 196))
            y += 16

        # Event ticker: the last few notable events up to the current turn
        # — the story of the match so far, wherever you've scrubbed to.
        # Rows are limited to what fits above the bottom-anchored Bot
        # Inspector: at small window heights the two used to overlap
        # (verified by screenshot at 1000x620).
        inspector_top = self._inspector_top()
        max_rows = max(0, (inspector_top - 8 - L["ticker_rows"]) // 15)
        if L["ticker_header"] + 14 > inspector_top:
            return
        draw_text(surface, "Events", (x + 12, L["ticker_header"]), size=12, color=(160, 165, 180))
        if max_rows == 0:
            return
        recent = [(t, txt) for t, txt in self._timeline if t <= frame["turn"]][-min(5, max_rows):]
        ty = L["ticker_rows"]
        if not recent:
            draw_text(surface, "Nothing yet.", (x + 12, ty), size=10, color=(120, 124, 138))
        for t, txt in recent:
            draw_text(surface, f"T{t}  {txt}", (x + 12, ty), size=10, color=(200, 203, 214))
            ty += 15

    # Base inspector height, plus extra room for the one-sentence bot
    # description that appears once a bot is selected. The extra is only
    # claimed while something is selected, so the Events ticker above
    # (which clips to _inspector_top) keeps its space the rest of the time.
    INSPECTOR_BASE_H = 150
    INSPECTOR_DESC_EXTRA = 42

    def _inspector_top(self) -> int:
        extra = self.INSPECTOR_DESC_EXTRA if self.selected_bot_id is not None else 0
        return self.screen_size[1] - (self.INSPECTOR_BASE_H + extra) - 8

    @staticmethod
    def _wrap_text(text: str, font: "pygame.font.Font", max_w: int) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            candidate = (cur + " " + word).strip()
            if font.size(candidate)[0] <= max_w:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def _draw_inspector(self, surface: "pygame.Surface", frame: dict) -> None:
        # Always visible (placeholder text when nothing's selected) rather
        # than only appearing once a bot is clicked — matches the Godot
        # HUD's persistent "Bot Inspector" panel, and means a first-time
        # user can see right away that bots are clickable at all.
        x = self.screen_size[0] - SIDEBAR_WIDTH
        y = self._inspector_top()
        rect = pygame.Rect(x + 8, y, SIDEBAR_WIDTH - 16, self.screen_size[1] - 8 - y)
        pygame.draw.rect(surface, (45, 48, 58), rect, border_radius=4)
        pygame.draw.rect(surface, (90, 95, 110), rect, width=1, border_radius=4)
        draw_text(surface, "Bot Inspector", (rect.x + 8, rect.y + 6), size=12, color=(160, 165, 180))

        bot = None
        if self.selected_bot_id is not None:
            bot = next((b for b in frame["bots"] if b["id"] == self.selected_bot_id), None)
        if bot is None:
            draw_text(surface, "Click a bot on the map to inspect it.", (rect.x + 8, rect.y + 28), size=11, color=(150, 150, 150))
            return

        ty = rect.y + 26
        draw_text(surface, f"#{bot['id']} {bot['type']}", (rect.x + 8, ty), size=11)
        ty += 16

        # One-sentence what-does-this-do, from the same data file as the
        # stats (data/bot_types.json) — a spectator shouldn't need the
        # guide open to understand what the thing they clicked is for.
        description = BotTypeRegistry.get_description(bot["type"])
        font10 = get_font(10)
        for line in self._wrap_text(description, font10, rect.width - 16)[:3]:
            draw_text(surface, line, (rect.x + 8, ty), size=10, color=(185, 188, 200))
            ty += 13
        ty += 3

        lines = [
            f"Owner: Player {bot['owner'] + 1}",
            f"HP: {bot['hp']}",
            f"AZN carried: {bot['azn']}",
            f"Position: {tuple(bot['pos'])}",
            f"Action: {bot['action']}",
            f"Alive: {bot['alive']}",
        ]
        for line in lines:
            draw_text(surface, line, (rect.x + 8, ty), size=11)
            ty += 15
