# v0.0.12 Changelog

**Version:** 0.0.12
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

When a player's spawn position (or a strategy's specifically requested
injection point) lands on Bone, the engine now picks a random passable
cell from the rest of the injection zone instead of deterministically
always the first one found in row-major order. Reproducible: uses the
match's own seeded RNG, so the same seed still produces the same spawn
point every time.

## Changed

- **`nanobot/core/simulation_core.py`**: `_default_injection_point()`'s
  fallback (used when the zone's literal corner is impassable — see
  v0.0.10) now collects every passable cell in the zone and picks one
  via `self._rng.choice(...)`, instead of returning the first match from
  a row-major scan. No change to the happy path (corner already
  passable) or to `_choose_injection_point()`'s own validation of a
  strategy's chosen point — only the fallback it defers to on failure.

## Added

- 2 new tests in `test_simulation_core.py`'s `TestDefaultInjectionPoint`:
  one confirming the fallback actually varies across different seeds
  (not secretly still deterministic), one confirming the *same* seed
  reliably reproduces the *same* spawn point across repeated runs (the
  reproducibility v0.0.2's whole "fully deterministic given a seed"
  property depends on).

## Verification

```
$ pytest tests/
301 passed in 0.93s

$ python tests/check_editor.py
ALL OK
```

Direct check on the real map this was found on
(`maps/vascular_network.json`), 4 different seeds:

```
seed 1 -> player 0 spawn: (1, 2)
seed 2 -> player 0 spawn: (2, 1)
seed 3 -> player 0 spawn: (4, 2)
seed 4 -> player 0 spawn: (4, 2)
```

All passable, all within the zone, visibly varying rather than always
landing on the same cell. A real headless match on the same map (seed 7)
completes normally end-to-end with both sides scoring.

## Known gaps carried forward

- Combat-effectiveness/defense-design question (v0.0.10) — still open.
- Contested-Habitas-Point scoring resolution (v0.0.8) — still open.
- No unit tests for the pygame rendering/widget layer — unchanged gap
  from every prior version.
