# v0.0.26 — Strategy Rock-Paper-Scissors Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Order

1. **Diagnose**: build the full head-to-head matrix → confirm a linear
   ladder (defense loses to nobody), not a cycle. Root cause: reactive
   defense is nearly free, so defense strictly dominates economy.
2. **Prototype** the missing edge: a greedy two-needle economy. Verify
   head-to-head it beats defense on the open map (2 needles out-score
   one fortified needle) and loses to combat everywhere.
3. **Rewrite `example_full_roster`** as that economy: claim + feed the
   two nearest points with two collectors; defense-light; a 40-AZN
   build reserve banked at the spawn zone so lost needles are
   reclaimed. Update the docstring (drops the "all 8 bots" showcase).
4. **Measure** the full app-faithful tournament + strict-king check;
   confirm no strategy beats the whole field.
5. **Verify**: pytest, editor check, loader.
6. **Docs**: README RPS note; this folder; commit + push.

## Explicit non-goals

- Eliminating the map-dependence of economy-vs-defense — it is *kept*
  (different maps favour different archetypes = good balance).
- Forcing `container` / the starter up — structural / separate (fix #4).
- Any engine/scoring/stat change — still pure strategy behaviour; wins
  stay the championship metric.
- Making the cycle "hard" (clean 2–0 edges everywhere) — soft edges +
  no strict king is the realistic, seed-robust target.
