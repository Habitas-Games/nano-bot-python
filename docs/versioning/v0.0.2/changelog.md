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

---

## Follow-up round 2: `starting_azn` was write-only, end-to-end

Found by re-reading `_init_match_state()`'s own comment ("Maps may declare a starting AZN value...") against what the code actually did, the same way the `MapHistory` bug surfaced — a comment describing intended behavior that the code next to it didn't implement.

**The gap:** every map JSON has always carried a `starting_azn` field, and the map editor's save path has always written one out — but `MapData` had no `starting_azn` attribute at all, `map_loader.load_from_file()` never read the field into anything, and `SimulationCore._init_match_state()` unconditionally used a hardcoded module constant regardless of what any map declared. A map author setting a custom starting budget had no way to actually do that; the field round-tripped as a write-only phantom. **Confirmed identical in the Godot original** — `map_data.gd` has no such field either, and `simulation_core.gd`'s `_init_match_state()` has the exact same "compute a fallback, then unconditionally overwrite it with the constant" dead-code shape. Inherited faithfully, not introduced by the port.

**Fix, end-to-end:**
- `MapData.__init__` now has a real `starting_azn: int = 150` attribute.
- `map_loader._parse_body()` reads `data.get("starting_azn", 150)` into it.
- `map_loader.create_json()`/`save_to_file()` now default to the `MapData`'s own value instead of a fixed `150` (an explicit `starting_azn=` argument still overrides it, for callers that want to).
- `SimulationCore._init_match_state()` now reads `self._map.starting_azn` instead of the module constant, which is now unused and removed (`DEFAULT_STARTING_AZN` deleted from `simulation_core.py`).
- `map_document_ops.snapshot()`/`restore()` now include `starting_azn` too — the `MapHistory` bug earlier in this version was caused by a partial snapshot silently breaking undo for whatever it excluded, and there's currently no editor UI to change this field, but keeping every `MapData` attribute covered by snapshot/restore avoids setting up the same trap for whenever that UI gets added. `restore()` tolerates snapshots taken before this field existed (`.get()` with a default) rather than raising.

**Verified four ways**, not just at the unit level: a real `SimulationCore.run()` with `starting_azn` set artificially low (5, below the 20 needed to build a `NanoCollector`) actually changes the match outcome — a strategy that previously scored 150+ scores 0, confirming this has real gameplay effect, not just changed data plumbing; the actual `MapEditorScreen` loading a map with `starting_azn: 777` correctly reflects it (`editor.doc.starting_azn == 777`); saving through the real UI save path round-trips that same custom value to JSON; both existing shipped maps still produce byte-identical match outcomes to before this fix (both specify exactly `150`, matching the old hardcoded default, so there is zero behavior change for any map that already exists — this only changes behavior for a map that declares something other than 150, which no shipped map currently does).

9 new tests (235 total). Full regression sweep green.

---

## Follow-up round 3: winner tie-break, confirmed with the user before fixing

While running a 3-strategy tournament to check round-robin scheduling at a larger size, noticed a "do nothing" strategy beat another "do nothing" strategy 2–0 purely because of list ordering. Traced to `_determine_winner()`: requirements.md SCO-04 documents a 3-level tie-break for equal scores — (1) bots still alive, (2) AZN collected, (3) turns elapsed — but the implementation just returned whichever player had the first-seen highest score, defaulting to player 0 on any tie, ignoring all three documented criteria. **Confirmed identical in the Godot original** (`simulation_core.gd`'s `_determine_winner()` has the exact same shape) — inherited, not introduced.

Unlike the `MapHistory` and `starting_azn` fixes, this one changes who actually wins a tied match on what's meant to be a competition platform, and the third documented criterion ("turns elapsed") is a single value for the whole match, not one per player, so it can never actually discriminate between two tied players — implementing it literally would be a no-op, not real tie-break logic. Both of those made this a decision for the user to weigh in on rather than something to silently decide, so it was raised explicitly before touching the code. Their call: implement criteria 1–2 (bots alive, AZN banked) and drop criterion 3 with that reasoning documented in the code rather than coded as a no-op.

**Fixed:** `SimulationCore._determine_winner()` now: finds the max score, checks for a tie; if tied, narrows by bots-still-alive; if still tied, narrows by `_player_azn_bank` (the only "AZN collected" value actually tracked); if still tied after both (fully symmetric state), falls back to first player_id — same as the old behavior, but now only as a last resort instead of the only resort.

Verified with 4 new tests: a tie broken by bots-alive, a tie broken by AZN-banked (after bots-alive was also equal), a fully-symmetric tie still falling back to player 0, and a clear non-tied score winning outright regardless of bots-alive/bank (confirming the tie-break machinery doesn't kick in when there's no tie to break). 238 tests total. Full regression sweep (pytest, editor integration script, real CLI match) confirms zero change to any non-tied match outcome, including both real shipped maps.

---

## Follow-up round 4: strategy-loading ambiguity — new to the port, not inherited

While testing a 3-strategy tournament, checked what `_load_strategy_instance()` does if a participant's `.py` file happens to define more than one `NanoStrategy` subclass (e.g. a leftover draft they forgot to delete, or a shared helper base class). It picked one — via `dir(module)`, which returns names in **sorted alphabetical order, not definition order** — meaning it would silently prefer whichever class name happens to sort first, with zero warning that a second candidate even existed.

**This is the one finding in this version that is not inherited from the Godot original** — confirmed by checking: a GDScript file structurally *is* exactly one class (`extends NanoStrategy` at the top level), so this ambiguity cannot arise there at all. It's a risk specific to porting to a language that allows multiple classes per file. A second, related gap: `dir(module)` also returns names merely *visible* in the module's namespace, including ones pulled in via `import` — a strategy file that imports a shared base class (itself a `NanoStrategy` subclass) would see that import as a second "candidate" too, even though it isn't defined in that file at all.

**Fixed:** restrict candidates to classes whose `__module__` actually matches the loaded module (excludes imported classes); if zero match, same "no subclass found" message as before; if more than one match, fail loudly with the names of all candidates rather than silently picking one — a participant should see this and fix their file, not debug a confusing "my strategy isn't doing what I coded" session caused by the wrong class quietly running.

7 new tests (`tests/test_strategy_loading.py`), 245 total. Full regression sweep green.

---

## Follow-up round 5: `BotTypeRegistry` — a real porting regression, not an inherited bug

Checked what happens with a missing or corrupted `data/bot_types.json` (`get_type()` is called constantly throughout `SimulationCore`'s action handlers — a crash here takes down the entire match, headless run, or app). Two real gaps, both confirmed by direct testing:

1. **Malformed JSON crashed with an unhandled `JSONDecodeError`.** Unlike every other finding in this version, this one is the *opposite* situation: the Godot original (`bot_type_registry.gd`) already checks `json.parse(...) != OK` and fails gracefully — the initial Python port used `json.load(f)` directly with no `try/except` at all, a missed translation, not an inherited issue. Fixed by catching `json.JSONDecodeError` and reporting the same way the existing missing-file branch already does.

2. **Syntactically-valid JSON that isn't an object (e.g. a bare array) parsed without error but crashed on first real use** — `get_type()`'s `_data.get(...)` raises `AttributeError` on a list. Lower-probability than a typo causing a parse error, but still a reachable crash from a malformed data file. Fixed by checking `isinstance(parsed, dict)` after a successful parse and treating a wrong shape the same as a parse failure.

7 new tests (`tests/test_bot_type_registry.py`), 252 total. Full regression sweep green, including confirming the real `data/bot_types.json` still loads correctly (this is the one file in the whole fix where "does the unmodified real data still work" needed explicit checking, since every other fix in this version dealt with hypothetical malformed input, not the actual shipped data file).

---

## Follow-up round 6: audited every JSON-loading call site for the same pattern

Finding the same crash shape twice in a row (`map_loader`, then `bot_type_registry`) was a signal to stop finding these one at a time and check systematically: `grep -rn "json\.load\b\|json\.loads\b" nanobot/` turned up exactly three call sites total. `map_loader.py` and `bot_type_registry.py` were already fixed; `match_log.py`'s `load_from_file()` was the one left unaudited.

It already caught `JSONDecodeError` correctly (no gap there), but had the same "valid JSON, wrong shape" hole as `bot_type_registry`: a bare JSON array or string parses without error, then every `data.get(...)` call crashes with `AttributeError` on first use. **This one matters more than most of this version's other findings** — `MatchLog.load_from_file()` sits directly on the path a user hits by opening a corrupted or incomplete replay file through the real `PlaybackViewer` UI, not just from hand-edited input. Fixed the same way as `bot_type_registry`: check `isinstance(data, dict)` after a successful parse, treat a wrong shape as a load failure.

Verified through the actual UI, not just the unit level: constructed a `PlaybackViewer` pointed at a corrupted (wrong-shape) replay file and confirmed `draw()` shows its existing "No replay loaded" fallback instead of crashing — `viewer.draw()` already had that fallback built in from v0.0.1, it just never got reached safely before this fix because the crash happened one level down, inside `load_from_file()` itself, before the viewer's own None-check ever ran.

This module had zero unit test coverage before this round (`tests/test_match_log.py` is new). 8 new tests, 260 total. Full regression sweep green.

---

## Follow-up round 7: a failed match could silently hang an entire tournament

Checked thread robustness next: `TournamentRunner._thread_main()` runs each scheduled match on a background thread with no top-level exception handling around the actual simulation (`sim.run()`) or its replay write (`log.save_to_file(...)`) — only the already-anticipated "map failed to load" case was handled.

**Confirmed directly, not hypothetically:** patched `SimulationCore.run()` to raise an unexpected exception (representing an engine bug, a disk-full error on the replay write, or anything else not already caught inside the simulation loop itself) and ran a real tournament. The background thread died — Python reports the traceback to stderr but does not crash the process — and **`on_tournament_finished` never fired, `self.results` stayed empty**. From `TournamentScreen`'s perspective: the progress bar would freeze at whatever match was in flight, permanently, with the Start button correctly disabled (so it can't be retried) and absolutely no indication anything had gone wrong — indistinguishable from a hang, with no recovery short of restarting the app.

**Fixed:** extracted the per-match body into `_run_one_match()` and wrapped each call to it in a `try/except Exception` inside the loop, recording any failure via the existing `_record_error()` mechanism (same one already used for "map failed to load") and continuing to the next scheduled match — exactly the same principle as `NFR-04` ("a runtime error inside a strategy file must not crash the simulation") one level up: a failure in one match must not be able to take down the rest of the tournament.

Verified three ways, including the multi-match scenario that proves recovery, not just isolation: a single failing match still fires `on_tournament_finished` and records a clean error result; a two-match tournament where only the *first* match is made to fail confirms the *second* match still runs and completes normally afterward, with the first correctly recorded as an error and the second correctly recorded as a real result.

`tournament_runner.py` had zero unit test coverage before this round (`tests/test_tournament_runner.py` is new, including round-robin schedule-size coverage that had only been spot-checked manually before). 9 new tests, 269 total. Full regression sweep green, including a real multi-strategy tournament via `run_tournament.py`.
