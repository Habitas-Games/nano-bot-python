# v0.0.2 — QA Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Unit-test the core engine and map-editor logic modules directly (pytest), bottom-up by dependency order, running the suite after every file so a failure is immediately attributable to the file just added rather than discovered in a pile at the end. For each module: cover the documented/spec'd behavior first (requirements.md's MAP-02/03 movement cost, SCO-01/02 scoring, etc.), then deliberately probe the edges (out-of-bounds, zero-capacity, duplicate placement, multi-step undo) rather than stopping at the happy path.

## Order

1. `core/map_data.py` — movement cost is the foundational formula everything else builds on.
2. `core/map_loader.py` — round-trip property, required-field strictness.
3. `core/grid_pathfinder.py` — cost-aware routing, not just reachability.
4. `core/nanobot_data.py` + `action_request.py` — quick, but pins down the stats-dict reading.
5. `core/simulation_core.py` — the big one; white-box test the action handlers and phase methods directly.
6. `ui/map_editor/map_document_ops.py` + `map_history.py` — the editor-specific logic, including undo.
7. `tournament/leaderboard.py` — scoring/DQ bookkeeping.
8. Full suite run, regression sweep against the existing v0.0.1 integration checks (the scripted editor-event script, a real headless CLI run, full app navigation) to confirm nothing in the test-writing process broke the parts that already worked.

## Tooling

- `pytest` added as a dev-only dependency (`requirements-dev.txt`, not bundled into the runtime `requirements.txt` — participants writing strategies don't need it).
- `pytest.ini` pointing `testpaths` at `tests/`.
- Existing one-off integration scripts (`tests/check_editor.py`) kept as-is alongside the new `test_*.py` pytest files — they test something the unit suite doesn't (real pygame event objects flowing through the actual `MapEditorScreen`), not a redundant duplicate.

## Explicit non-goals for this version

- No tests for the pygame rendering/input layers themselves (`map_canvas_renderer.py`, `playback_viewer.py`, tool classes' event handling, `main_menu.py`'s background-thread wiring) — these have scripted integration coverage from v0.0.1 but no unit tests. Natural v0.0.3 scope if it matters before then.
- No CI wiring (GitHub Actions etc.) — out of scope until/unless this project gets pushed somewhere CI would run.
- No mutation testing or coverage-percentage target — the goal was "catch real bugs in central logic," which it did, not "hit a number."
