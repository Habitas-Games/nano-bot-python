# v0.0.2 — QA Analysis

**Status:** Complete
**Depends on:** [../v0.0.1/changelog.md](../v0.0.1/changelog.md) (which named this scope explicitly: "No automated test suite (pytest) — see plan.md's non-goals... A real test suite is the natural v0.0.2 scope")

---

## 1. What v0.0.1 actually verified, and the gap

v0.0.1's verification (its own changelog §"Verification performed") was real but coarse: a handful of end-to-end smoke runs (one full match, one CLI invocation, one tournament, a scripted sequence of map-editor UI events, some rendered screenshots) plus a UX pass that fixed five issues found by *looking* at output. None of it was structured to catch a logic bug in a rarely-exercised code path — e.g. nothing in v0.0.1 ever called `MapHistory.undo()` twice in a row, which turned out to matter (§3 below).

This version's job: systematic unit coverage of the modules everything else depends on, run in a way that's fast enough to execute on every change (the full suite runs in well under a second), specifically targeting edge cases the smoke tests structurally couldn't reach — boundary coordinates, build/collect/transfer validation failures, multi-edit undo sequences, tie-breaking, disqualification bookkeeping.

## 2. What was tested and why those modules specifically

| Module | Why it's worth unit-testing in isolation |
|---|---|
| `core/map_data.py` | The movement-cost formula (density + stream bonus/penalty + minimum clamp) is the single most load-bearing piece of arithmetic in the whole project — pathfinding, movement, and every strategy's planning all sit on top of it. |
| `core/map_loader.py` | This module exists *specifically* to be the one place JSON↔MapData happens (v0.0.1 analysis.md §3) — its round-trip property (`load(save(x)) == x`) is the thing that consolidation was supposed to guarantee, so it needed to be checked, not assumed. |
| `core/grid_pathfinder.py` | A custom directed-edge A* — cost-awareness (not just hop-count) under streams and density variation is exactly the kind of thing that "looks right" on a quick read but needs a constructed counter-example to actually verify. |
| `core/nanobot_data.py`, `action_request.py` | Small, but a renamed dict key in `bot_types.json` failing silently (`dict.get` with a default) is a real risk class — worth pinning down explicitly. |
| `core/simulation_core.py` | The center of the whole port. Tested its action handlers directly (white-box) rather than only through full strategy files, since the interesting behavior — build adjacency/cost validation, collect/transfer capacity clamping, attack range and friendly-fire exclusion, auto-destruct, NanoAI-death gating, the exact scoring formula, end-condition counting, tie-breaking — lives in those methods, and a thrown-together strategy file per scenario would have obscured what was actually under test. |
| `ui/map_editor/map_document_ops.py`, `map_history.py` | Carries the specific fixes the Godot port's v0.0.3 cleanup made (duplicate-placement guard, whole-document undo snapshots) — these are exactly the kind of "fixed it, but did I actually verify the fix" claims that deserve a regression test, not just a one-time manual check. |
| `tournament/leaderboard.py` | Disqualification bookkeeping (a DQ flag that must persist once set, the "exactly one side DQ'd" branch) has enough conditional branching to be worth covering directly. |

Not yet covered: the pygame rendering/input layers themselves (`map_canvas_renderer.py`, `playback_viewer.py`, the tool classes' pygame-event handling, `main_menu.py`'s threading) — these were exercised via the scripted integration checks in v0.0.1 and the UX pass, but don't have unit tests. Reasonable next scope, not done here.

## 3. Bug found: `MapHistory.undo()` off-by-one

**This is the one finding that matters most from this pass.** Writing `test_one_undo_reverts_only_the_most_recent_of_two_edits` (deliberately constructed to match the *exact* calling convention every tool actually uses — `save_state()` immediately before each discrete mutation, including the first one after load) exposed that a single Undo click, after two separate edits, reverted **both** edits at once instead of just the most recent one.

**Root cause:** `save_state()` is always called *before* a mutation, so `_history[_index]` already holds "the state right before the most recently completed edit" — exactly what one Undo should restore. The old `undo()` decremented `_index` *first*, then restored — which reads the *previous* entry instead, one step too far back.

**This bug was not introduced during the Python port.** It was faithfully translated from the Godot version's `_undo()`, which has the identical decrement-then-restore order. It's a pre-existing logic bug in the reference implementation that survived because a single edit followed by a single undo — the only scenario any manual test (in either codebase) seems to have exercised — happens to produce the correct-looking result by coincidence (restoring the baseline either way, when there's only one edit on top of it). It only diverges from two edits onward.

**Fix:** restore `_history[_index]` first, then decrement, in `nanobot/ui/map_editor/map_history.py:undo()`. Verified two ways: the unit test, and a separate scripted check driving the real `MapEditorScreen` through two real button-click placements followed by one real Undo click, confirming exactly one habitas point comes back.

This is reported back to the Godot project's own backlog as a known carry-over bug, since it affects that implementation identically and wasn't caught there either.

## 4. Process note

Two of the three initial test failures in this pass were bugs in the *tests themselves* (out-of-bounds coordinates on a 5×5 test map; a corner-detection test whose zone was too small for any point to be far from every corner) — caught and fixed before concluding anything about the application code. The third (`MapHistory`) looked like a test-authoring mistake at first too, and turned out not to be, once the test was rewritten to match the real calling convention exactly. Worth recording: the discipline that mattered here wasn't "write tests," it was "when a test fails, work out *which side* is wrong before touching either."
