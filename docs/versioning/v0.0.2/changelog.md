# v0.0.2 Changelog

**Version:** 0.0.2
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Added a 218-test pytest suite covering the core simulation engine and map-editor logic. Found and fixed one real, pre-existing bug along the way (see below) — not introduced by the Python port, inherited identically from the Godot version, and never caught by either codebase's manual testing.

## Added

- `requirements-dev.txt` (pytest, layered on top of `requirements.txt`), `pytest.ini`.
- `tests/test_map_data.py` — 21 tests: bounds, passability, movement cost (density + stream bonus/penalty + minimum clamp) for all four stream directions.
- `tests/test_map_loader.py` — 34 tests: enum↔string conversion, required-field enforcement, sparse-encoding round-trip, validation.
- `tests/test_grid_pathfinder.py` — 11 tests: basic pathing, unreachable/impassable targets, cost-aware routing under density variation and streams, `path_cost()` consistency.
- `tests/test_nanobot_data.py` — 17 tests: stats-dict reading, damage/death, log serialization.
- `tests/test_action_request.py` — 10 tests: all 8 factory methods, type names.
- `tests/test_simulation_core.py` — 57 tests: build validation (adjacency, cost, unknown type, bone target), collect/transfer capacity and rate limits, attack range and friendly-fire exclusion, auto-destruct countdown, NanoAI-death gating, the exact scoring formula (5pts / 20+2×azn), end-condition counting and winner tie-breaking, movement blocking (enemy walls/blockers, density immunity), a full no-strategy match run, determinism for a fixed seed.
- `tests/test_map_document_ops.py` — 44 tests: paint/flood-fill, clear/delete, duplicate-placement guards, element find/move, zone corner detection and resize, snapshot/restore.
- `tests/test_map_history.py` — 9 tests, including the one that caught the bug below.
- `tests/test_leaderboard.py` — 15 tests: win/loss/draw crediting, points accumulation, disqualification bookkeeping and persistence, sort order.

## Fixed

**`MapHistory.undo()` off-by-one (`nanobot/ui/map_editor/map_history.py`).** A single Undo click, after two separate edits, reverted both at once instead of just the most recent one. Root cause: `undo()` decremented its index pointer *before* restoring, when `save_state()`'s "always called right before a mutation" convention means the entry at the *current* index already holds exactly the right target for one Undo. Restoring before decrementing fixes it.

This bug was inherited from the Godot version's `_undo()` (identical decrement-then-restore order), not introduced during the port. It survived in both codebases because a single edit followed by a single undo — apparently the only scenario manual testing exercised in either project — produces the correct-looking result by coincidence. See analysis.md §3 for the full trace.

Verified two ways:
- `tests/test_map_history.py::test_one_undo_reverts_only_the_most_recent_of_two_edits`
- A scripted check driving the real `MapEditorScreen` through two genuine button-click habitas placements followed by one real Undo click, confirming exactly one placement reverts (not both).

## Also fixed (incidental, found while writing tests)

Two test-authoring bugs caught and corrected before they could be mistaken for application bugs:
- `test_map_data.py`: an early draft used grid coordinates outside a 5×5 test map's bounds.
- `test_map_document_ops.py`: a corner-detection test used a 4×4 zone too small for any interior point to be more than 1.5 cells from *every* corner, making "this point shouldn't match any corner" untestable at that size.

## Verification

```
$ pytest tests/
218 passed in 0.16s
```

Plus a full regression sweep after the `map_history.py` fix: the existing `tests/check_editor.py` integration script, a real `run_headless.py` CLI invocation, and full app screen navigation (menu → editor → tournament → menu) — all still pass, confirming the undo fix didn't disturb anything the v0.0.1 smoke tests already covered.

## Known gaps carried forward

- No unit tests for the pygame layers (renderer, playback viewer, tool event handling, main menu's threading) — see plan.md's non-goals.
- No CI wiring.

---

## Follow-up round: exhaustive CLI/error-path sweep

A second verification pass after the above, going beyond the happy paths the original test-writing covered: every map×strategy pairing through the real CLI, a full tournament run, malformed-input edge cases (missing CLI args, nonexistent files, a strategy with a Python syntax error, a strategy that raises on every single turn), and a final round of full-app screenshots.

**Found and fixed two real robustness gaps in `core/map_loader.py`:**

1. A map JSON with a non-numeric cell coordinate (e.g. `{"x": "not_a_number", ...}`) raised an unhandled `ValueError` out of `load_from_file()` instead of returning `None` with a clean error message like every other malformed-input case in that function already did. Hand-edited or corrupted map files are exactly the input this needs to survive. Fixed by wrapping the cell/element-parsing body in a try/except that catches `KeyError`/`ValueError`/`TypeError` and reports the failure the same way.

2. A non-positive width or height (e.g. `{"width": -5, "height": 10}`) was silently accepted, producing a `MapData` with `width=-5` and **zero actual cells** (`range(-5*10)` is empty) rather than being rejected — a map in this state would make every coordinate incorrectly report as out-of-bounds wherever it was later used, a confusing failure far from its actual cause. Now rejected at load time with a clear message.

Both verified with new regression tests (`tests/test_map_loader.py`, 8 new cases) and confirmed the fix doesn't reject legitimate input (numeric-string dimensions like `{"width": "10", ...}`, which `int()` handles fine, still load correctly).

**Confirmed working correctly, not bugs:**

- `example_strategy_v2.py` scores 0 when assigned to player slot 0 on `maps/vascular_network.json` specifically — traced to the cells immediately adjacent to that map's player-0 spawn corner `(0,0)` both being `BONE` (impassable), which the strategy's naive `_adjacent_free()` (checks only the 4 cardinal neighbors, never tries moving first) can't get around. This is a faithful, line-for-line port of the same heuristic from the Godot version and would behave identically there — a property of (this example strategy × this map's terrain layout), not an engine defect. The engine's behavior (BONE blocks building, exactly per spec) is correct.
- `NFR-04` error isolation confirmed directly: a strategy file with a Python syntax error, and a separate strategy that raises an exception on every single turn, both produce a clean per-turn/per-load error log without crashing the match — the well-behaved opponent wins normally in both cases.
- Engine pads to 2 players when only 1 strategy is supplied, matching `_player_count = max(len(strategy_paths), 2)`.
- In-app error modal in the map editor confirmed not to crash on a corrupt file passed through the real `MapEditorScreen._load_map_from_file()` path (shows a generic "Failed to load" message rather than the specific reason — a minor polish gap, not a defect, left as-is).

Full suite: 226 tests (up from 218), 0.16s. Final regression sweep (pytest, editor integration script, real CLI match, full app screenshot pass) all green.
