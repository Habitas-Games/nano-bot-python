# v0.0.8 — Engine Fixes & Full Strategy Roster Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Verify every bot mechanic actually works before writing a demo around
it — reading the description in the participant guide is not
verification, since that guide was itself ported faithfully from Godot
in v0.0.6 and could carry forward the same gap. Fix what's broken at the
engine level first (with the user's explicit sign-off, since it affects
match outcomes), then write the demos, testing each one by actually
running it — including as both player slots, since nothing before this
version had ever exercised a strategy as player 1.

## Order

1. Audit the five not-yet-demonstrated bot types/mechanics
   (NanoExplorer, NanoContainer, NanoIPCreator, NanoBlocker, NanoWall,
   defend()) against the actual `simulation_core.py`/`map_data.py` code.
   Found three non-functional; confirmed NanoBlocker/NanoWall/defend()
   already work correctly.
2. Asked the user how to proceed given the findings (analysis.md §2) —
   their choice: fix all three, build demos around the real mechanics.
3. Fix `MapData.movement_cost()` (density immunity), thread it through
   `GridPathfinder`. Fix `_action_transfer()` (NanoContainer). Fix
   `_action_open_ip()` (a real per-match injection-zone list). Add
   regression tests for each at the point of the fix, not afterward —
   `test_map_data.py`, `test_grid_pathfinder.py`, and
   `test_simulation_core.py` all gained new cases in the same pass as
   the corresponding fix.
4. Write the five focused demos in dependency order matching how
   participants would naturally build complexity: `example_explorer.py`
   (simplest — one extra unit, one extra movement rule) ->
   `example_container.py` (one extra relay hop) -> `example_defense.py`
   (two extra units, no new resource-flow concept) ->
   `example_combat.py` (introduces a second collector with a different
   job) -> `example_ip_creator.py` (the most state-dependent one, tracks
   a discovered position across turns).
5. Write `example_full_roster.py` last, combining all five — and
   specifically *because* writing it last surfaced two further bugs
   (analysis.md §4) that the simpler demos' shorter, single-purpose
   logic never exercised: a feedback loop between the funding mechanism
   and the wall's recurring upkeep cost, and an early-abandonment bug in
   the delivery logic that the simpler demos' short delivery routes never
   made expensive enough to notice.
6. Test every one of the six new files as **both** player 0 and player
   1 — surfaced the position-heuristic bug (analysis.md §5) that testing
   only as player 0 (matching every prior test in this project's
   history) would never have caught.
7. Run a full 8-strategy round-robin tournament as a final integration
   check — confirms all six new files coexist with the two existing ones
   without crashing, and that none of them regress to scoring 0 like the
   deliberately-naive starter does.
8. Update `README.md`'s strategy-writing section and stale test count;
   leave `docs/participant_guide.html` as-is (its walkthrough section
   already names `example_strategy_v2.py` specifically, which is still
   accurate — the new files are reference strategies, not part of the
   guided walkthrough).

## Verification

- Every engine fix verified two ways: a direct unit test, and (for the
  two found while building the demos) an actual match replay traced
  turn-by-turn to confirm the root cause before fixing it.
- Every one of the six new strategy files run as a real headless match,
  individually, against both `example_strategy.py` and
  `example_strategy_v2.py`, as both player 0 and player 1.
- A full tournament across all 8 strategy files in `strategies/`.
- Full existing test suite (`pytest`, `tests/check_editor.py`) re-run
  after every engine change, not just at the end.

## Explicit non-goals for this version

- Not fixing the contested-Habitas-Point scoring behavior
  (analysis.md §6) — discovered, reported, not decided on without the
  user, the same way the v0.0.2 tie-break wasn't.
- Not modifying `example_strategy.py` or `example_strategy_v2.py` — both
  are existing, already-shipped reference strategies used throughout
  this project's history as trusted baselines; the position-heuristic
  fix and the delivery-priority fix only apply to the six new files.
- Not adding fog-of-war / limiting `visible_enemies` by NanoExplorer's
  scan radius — `nano_strategy.py` already documents this as a future
  milestone in both the Python port and the Godot original, unrelated to
  this version's scope (density immunity, not visibility).
