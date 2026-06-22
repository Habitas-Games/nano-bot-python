# v0.0.10 — Every Strategy Should Score Analysis

**Status:** Complete
**Depends on:** [../v0.0.9/changelog.md](../v0.0.9/changelog.md)

---

## 1. Trigger

"All strategies should make some points at least." Checked this
directly rather than assuming the v0.0.8 tournament's healthy-looking
leaderboard totals meant every match went fine — totals can hide a
strategy that scores big in some matches and exactly 0 in others.

## 2. Auditing every individual match, not just leaderboard totals

Re-ran the full 8-strategy round-robin and, instead of reading the
aggregated leaderboard, scanned every individual saved replay's
`final_scores` for an exact 0. Before any fix: every one of the 7
demo strategies (everything except the brand new `example_combat`)
scored exactly 0 in somewhere between 2 and 7 of its 14 matches —
`example_strategy.py` in all 14.

## 3. Three distinct, separable causes found

- **`example_strategy.py` was guaranteed to score 0 always**, by
  design — it moves bots toward a Habitas Point but never builds a
  needle, so it structurally cannot score under any circumstances. Not
  a bug exactly (it never claimed to score), but not useful as a
  "starter" if copying it verbatim and adjusting later is the expected
  workflow, and not what "all strategies should make some points" wants
  from a file that ships as one of the 8.

- **A real engine bug: a player's default spawn point could be on an
  impassable cell.** Traced `example_container`'s 0-point loss to even
  the weakest possible opponent (`example_strategy`, which does
  nothing) by checking the final frame: `example_container`'s NanoAI
  was still sitting at `(0, 0)`, having built nothing in 1500 turns.
  `maps/vascular_network.json`'s player-0 injection zone is `(0,0)-
  (4,4)` — a 5x5 area that's fully passable *except* for a Bone border
  that happens to seal exactly the `(0, 0)` corner. `_default_injection_
  point()` blindly returns the zone rect's literal corner with no
  passability check, so the NanoAI spawned directly on the one
  impassable cell in an otherwise fine zone — with both cardinal
  neighbors of `(0, 0)` also Bone (confirmed: the entire border row/
  column is Bone), there was no path out at all. Not a strategy bug —
  no strategy, however written, can route around a cell pathfinding
  correctly determines is unreachable. Confirmed identical in the Godot
  original's `_default_injection_point()` (same blind corner-return, no
  passability check) — inherited, not a Python-port regression.

- **All six v0.0.8 strategy files (plus `example_strategy_v2.py`, not
  touched in v0.0.8) measured "nearest Habitas Point" from a hardcoded
  `(0, 0)`** — already found and fixed in the six new files during
  v0.0.8, but `example_strategy_v2.py` itself was deliberately left
  untouched there as "an existing, already-shipped reference strategy,
  out of scope." The user's "all strategies" framing this round
  supersedes that earlier caution — it explicitly includes every file
  in `strategies/`, not just the ones added in the previous version.

## 4. What's left, and why it's not being fixed

After all three fixes, the *only* remaining 0-point matches (exactly 2
per strategy, both against `example_combat`) are real combat losses —
confirmed by checking that `example_combat`'s fighter actually destroyed
the opponent's NanoAI/needle in each case, the same verified mechanism
already confirmed working in v0.0.8. This is `defend()`/attack
functioning as designed, not a bug: NanoBlocker and NanoWall only block
*movement* through their own cell (`_find_enemy_wall`/
`_find_enemy_blocker`), which does nothing against a ranged attacker 12
cells away — so `example_defense.py`'s fortifications, real as they are,
don't actually protect against this specific threat. Whether combat
should be softened, or economic strategies should be expected to defend
against it some other way, is a balance/design question the same way
the v0.0.2 tie-break and v0.0.8 contested-point findings were — reported
here, not decided unilaterally.
