# v0.0.12 — Randomized Injection-Point Fallback Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Replace the row-major "return the first passable cell found" loop with
"collect every passable cell, then `self._rng.choice(...)`" — same
candidate set, different selection rule. Use the match's existing seeded
RNG, not a fresh one, to preserve determinism-given-a-seed.

## Order

1. Edit `_default_injection_point()`'s fallback branch: build a list
   comprehension of every passable `(x, y)` in the zone, then
   `self._rng.choice(candidates)` instead of returning on first match.
2. Re-run the three existing v0.0.10 tests unchanged — none of them
   assert *which* specific cell gets picked in the multi-candidate case,
   so all three still pass without modification.
3. Add two new tests: one confirming the choice actually varies across
   different seeds (not secretly still deterministic), one confirming
   the *same* seed reliably reproduces the *same* spawn point across
   repeated runs.
4. Verify on the real map this was originally found on
   (`maps/vascular_network.json`): run with several different seeds
   directly and confirm the player-0 spawn point varies and is always
   passable; run a real headless match end-to-end to confirm scoring
   still works normally.

## Verification

```
$ pytest tests/
301 passed in 0.93s

$ python tests/check_editor.py
ALL OK
```

Direct check against `maps/vascular_network.json` across 4 seeds:
spawns of `(1,2)`, `(2,1)`, `(4,2)`, `(4,2)` — varied, all confirmed
passable. A real headless match on the same map (seed 7) completes
normally with both sides scoring.

## Explicit non-goals for this version

- No change to the happy-path case (corner already passable) — verified
  by the unchanged `test_still_uses_the_corner_when_it_is_passable`.
- No change to `_choose_injection_point()`'s own validation logic (a
  strategy's chosen point is still checked for zone-membership and
  passability the same way); only the *fallback* it defers to when that
  check fails is now randomized.
