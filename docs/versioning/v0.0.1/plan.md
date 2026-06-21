# v0.0.1 — Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

**Note on process:** unlike the Godot project's versioning docs (written
phase-by-phase, before each phase's implementation), this plan was
written to capture the milestone order actually followed during a single
continuous porting session, immediately after the port. The order below
is what happened, in the sequence it happened, kept as a plan document
because the convention established in the Godot project's v0.0.3 cleanup
is "every version gets an analysis.md/plan.md/changelog.md, full stop" —
not because the order needed deciding in advance this time. Future
versions of this project should write plan.md *before* implementing, as
v0.0.1 of the Godot project did.

---

## Milestone order

### 1. Core engine (`nanobot/core/`)

`map_data.py` → `map_loader.py` → `bot_type_registry.py` →
`nanobot_data.py` → `action_request.py` → `grid_pathfinder.py` (A* with a
binary heap instead of the Godot version's linear-scan open list — a
straight upgrade, not a behavior change) → `match_log.py` →
`simulation_core.py`, in that dependency order. No pygame import anywhere
in this package — it must run with nothing but the standard library.

### 2. Strategy API (`nanobot/api/`)

`nano_strategy.py`, `cell_info.py`, `habitas_point_info.py`,
`azn_node_info.py`, `map_info.py`, `bot_proxy.py` — mirrors the Godot
`src/api/` package one file at a time.

### 3. Data + example strategies

Copied `data/bot_types.json` and both existing maps unchanged (verified
byte-for-byte compatible — same `width`/`height`/`cells`/`habitas_points`/
`azn_nodes`/`injection_zones` schema). Ported both example strategies
(`example_strategy.py` — naive, moves toward the first Habitas Point;
`example_strategy_v2.py` — builds a Collector then a Needle and actually
scores) since having one strategy that scores 0 and one that scores >0 is
the simplest possible test of the whole simulation pipeline.

### 4. Headless runner + tournament runner

`nanobot/runner/headless_runner.py` and `run_headless.py`, then
`nanobot/tournament/{tournament_runner,leaderboard}.py` and
`run_tournament.py`. Verified each as a real CLI invocation before moving on.

### 5. Map editor (`nanobot/ui/map_editor/`)

Applied the Godot v0.0.3 refactor's architecture directly rather than
starting from the original (pre-refactor) editor's mistakes:
`map_document_ops.py` (free functions over `MapData`) →
`map_history.py` (whole-document snapshots from the start) →
`map_canvas_renderer.py` → `tools/` (one class per tool, same interface
shape as the Godot version's `EditorTool` base) → `map_editor_sidebar.py`
→ `map_editor.py`. Caught and fixed one real layout bug here (sidebar/
canvas rect overlap) by driving the screen with synthetic events instead
of only reading the code back.

### 6. Playback viewer + main menu + tournament screen

`nanobot/ui/playback/playback_viewer.py`, `nanobot/ui/main_menu.py`,
`nanobot/ui/tournament/tournament_ui.py`, then `main.py` wiring all four
screens (menu, editor, playback, tournament) together with simple
callback-based navigation.

### 7. Verification pass

Headless pygame integration checks for every screen, then real PNG
screenshots via SDL's dummy driver, visually inspected — see
analysis.md §4 and changelog.md.

---

## Explicit non-goals for v0.0.1

- No automated test suite (pytest) yet — verification was manual/scripted
  integration checks. A real test suite is the natural v0.0.2 scope.
- No fog-of-war / scan-range-limited visibility for `visible_enemies` —
  matches the Godot version's own "all enemies visible for now" note in
  `map_info.gd`.
- No script sandboxing for strategy files (see requirements.md §3).
- Only the 2 maps and 2 example strategies that existed in the Godot
  project were ported; requirements.md's "ships with 3+ maps" is not yet met.
