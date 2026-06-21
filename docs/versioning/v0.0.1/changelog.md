# v0.0.1 Changelog

**Version:** 0.0.1
**Status:** Complete
**Date:** 2026-06-21

---

## Summary

Full Python/pygame port of the Godot `nano-bot` project: core simulation
engine, strategy API, headless runner, tournament runner + leaderboard,
pygame map editor, pygame replay viewer, and a main menu tying them
together. Simulation rules, scoring, bot stats, and JSON formats are
unchanged from the Godot version (see analysis.md §1-2 for the porting
decisions).

## What was built

- `nanobot/core/`: `map_data.py`, `map_loader.py` (load+save+validate, single canonical home — see analysis.md §3), `bot_type_registry.py`, `nanobot_data.py`, `action_request.py`, `grid_pathfinder.py` (A* via `heapq`), `match_log.py`, `simulation_core.py` (full turn loop, byte-for-byte phase order match with `simulation_core.gd`).
- `nanobot/api/`: `nano_strategy.py`, `map_info.py`, `cell_info.py`, `habitas_point_info.py`, `azn_node_info.py`, `bot_proxy.py`.
- `nanobot/runner/headless_runner.py` + `run_headless.py` CLI.
- `nanobot/tournament/{tournament_runner,leaderboard}.py` + `run_tournament.py` CLI.
- `nanobot/ui/map_editor/`: `map_document_ops.py`, `map_history.py`, `map_canvas_renderer.py`, 8 tool classes under `tools/`, `map_editor_sidebar.py`, `map_editor.py`.
- `nanobot/ui/playback/playback_viewer.py`: animated replay with play/pause/step/speed, HUD, click-to-inspect.
- `nanobot/ui/main_menu.py`, `nanobot/ui/tournament/tournament_ui.py`, `main.py`.
- `data/bot_types.json`, `maps/simple_tissue.json`, `maps/vascular_network.json`, `strategies/example_strategy.py`, `strategies/example_strategy_v2.py` — copied/ported from the Godot project.

## Bugs found and fixed during the port (not present in the plan, found via verification)

**Map editor sidebar/canvas rect overlap.** `MapEditorSidebar` was
positioned at `x=0` (same as the canvas) instead of the right edge
(`screen_width - PANEL_WIDTH`). Caught by driving the editor with
synthetic pygame events end-to-end: clicking what should have been an
AZN node at screen position `(104, 354)` instead activated the Pan tool,
because that pixel landed inside the (wrongly-positioned) sidebar's "Pan"
button hitbox. Fixed by positioning the sidebar's rect at the right edge
and offsetting every button's x-coordinate from `self.rect.x` instead of
a hardcoded `0`. This is the same class of bug as the Godot project's
v0.0.2 "exclusive tool mode" issue (UI elements with overlapping input
regions both responding to one click) — caught here in minutes instead of
across several user-reported sessions, specifically *because* the
verification step was "drive it with real events and check the resulting
state," not "read the code and confirm it looks right."

## Verification performed

- **Core simulation:** ran a real 1500-turn match via `SimulationCore` directly — completed in 0.06s (requirement: ≤5s for 50×50; this map is 80×80 and still ~80x under budget). Ran `example_strategy_v2` (builds Collector + Needle) vs `example_strategy` (naive) — v2 scored 150 points, confirming build/move/collect/transfer/score all work end-to-end; the naive strategy scored 0, as expected since it never places a NanoNeedle.
- **Headless runner:** invoked as a real subprocess: `python run_headless.py --map maps/simple_tissue.json --strategy_a ... --strategy_b ... --seed 7`. Produced a valid replay JSON with the expected `{map_name, player_strategies, total_turns, final_scores, winner_id, frames}` structure; spot-checked frame contents.
- **Tournament runner:** invoked as a real subprocess: `python run_tournament.py` over 2 strategies × 2 maps (4 round-robin pairings → 2 unique matches since round-robin only pairs each combination once per map... actually 2 strategies × 2 maps = 2 matches, one per map). Leaderboard correctly ranked `example_strategy_v2` 2W-0L-350pts above `example_strategy` 0W-2L-0pts.
- **Map editor:** drove `MapEditorScreen` with synthetic `pygame.event.Event` objects (mouse down/move/up, key down) covering: terrain paint, habitas placement + duplicate-position guard + undo (confirmed undo actually removes the placed point — this is the fix from analysis.md §3's "undo snapshots everything" decision, verified directly rather than assumed), zone drag-to-place, zone corner detection + resize, AZN inline quantity edit, save-then-reload round trip. Found and fixed the sidebar overlap bug during this pass (see above).
- **Playback viewer:** loaded a real replay file, drew multiple frames, stepped and played back at a chosen speed (confirmed exactly 8 frames advance per second of wall-clock time at 1.0x — matches the hardcoded 8 turns/sec base rate × speed multiplier), clicked a bot to open the inspector panel, confirmed displayed stats matched the underlying frame data.
- **Full app, visually:** rendered all four screens (main menu, map editor, playback viewer with inspector open, tournament screen after a completed run) to real pixel buffers via SDL's dummy video driver (`SDL_VIDEODRIVER=dummy`) and saved them as PNGs, then visually inspected the images rather than only checking that no exception was raised. Confirmed: sidebar correctly on the right with no overlap, terrain/stream/habitas/AZN all rendering with correct textures and colors, HUD showing correct per-player scores and bot-alive counts, the injection-zone-validation-with-fallback logic visibly working (the naive strategy's chosen injection point fell outside its assigned zone and correctly fell back to the zone's default corner), and the tournament leaderboard rendering with correct win/loss/points columns.

## Known gaps (carried into a future version, not silently dropped)

- No automated test suite (pytest) — see plan.md's non-goals.
- Tournament progress callbacks fire directly from the background thread without marshalling to the main thread first (analysis.md §3) — acceptable for a progress display, would need fixing for anything correctness-sensitive.
- Only 2 of the requirements doc's "3+ shipped maps" exist (carried over unchanged from the Godot project, which also only had 2).
