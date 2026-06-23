# v0.0.12 — Randomized Injection-Point Fallback Analysis

**Status:** Complete
**Depends on:** [../v0.0.11/changelog.md](../v0.0.11/changelog.md)

---

## 1. Trigger

"If the selected position of the player for start is bone then random
among the valid positions on the injection area without bones." A
refinement of v0.0.10's fix: that version made
`_default_injection_point()` search the rest of the zone for *any*
passable cell when the zone's literal corner is Bone, but the search was
deterministic — row-major order, always returning the first passable
cell found. This version makes that fallback a random pick among every
passable cell in the zone instead of always the same predictable one.

## 2. Scope: only the fallback, not the happy path

This only changes what happens when the originally-selected position
(the zone's corner, or — by way of `_choose_injection_point()` falling
through to the same function — a strategy's specifically requested
point) turns out to be impassable. When the corner is already passable
(the common case: every existing test fixture, both bundled maps'
player-1 zones, and player-0 zones on any map without this specific
bone-corner defect), nothing changes — no randomization is introduced
where there was nothing to fall back from.

## 3. Reproducibility

`SimulationCore` already maintains a seeded `random.Random` instance
(`self._rng`, seeded from the match's `seed` parameter) for combat
damage rolls — using the same instance here means a given seed still
produces the exact same match deterministically end-to-end, including
which fallback spawn point gets picked, consistent with the project's
existing "fully deterministic given a seed" property. A fresh,
unseeded `random` call would have broken that.
