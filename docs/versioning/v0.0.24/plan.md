# v0.0.24 — Strategy Rebalance Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Measure first (the project's rule for balance). Diagnose why combat
wins by re-running the tournament under each candidate lever; isolate
the minimal effective reflex head-to-head; package it once; wire it
into the passive economy demos; re-measure the whole field.

## Order

1. **Diagnose**: tournament under needle-HP / collector-nerf /
   unkillable-AI / cumulative-scoring — all leave combat 13–14, ruling
   out stat and scoring fixes. Trace shows elimination (match ends
   ~turn 275) is the mechanism.
2. **Isolate the reflex**: strategy_v2-vs-combat under shoot-only /
   wall-only / shoot+wall / full — only watchtower+wall+shoot flips it
   (0→17), and all three pieces are needed.
3. **`nanobot/api/reactive_defense.py`**: `ReactiveDefenseMixin`
   (`run_defense_ai`, `park_watchtower`, `shoot_back`) + self-contained
   geometry. In the package, not `strategies/`, so the loader won't
   treat it as a competitor.
4. **Wire** strategy_v2, container, ip_creator: inherit the mixin, call
   its methods once the needle exists; economy build order runs first,
   defense takes the NanoAI after.
5. **Re-measure** the 56-match tournament; confirm combat off the top
   and the field competitive; confirm the zero-score invariant.
6. **Verify**: loader picks only the strategy class; full pytest;
   editor check.
7. **Docs**: README strategy note, guide defence tip, this folder;
   commit + push.

## Explicit non-goals

- Touching `example_combat` (aggressor), `example_defense` (already
  defensive), `example_explorer` (competitive speed-demo),
  `example_full_roster` (own defense) — no rebalance needed.
- `example_strategy` the starter (0W) — that's fix #4, a separate
  decision the user hasn't taken yet.
- Making `container` a winner — its relay keeps the collector away
  from the needle by design; the reflex extends its survival, not its
  win rate. Honest limit, not a bug.
- Any engine/scoring/stat change — the collector's dual role is canon;
  wins-as-champion stays.
