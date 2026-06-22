# v0.0.10 Changelog

**Version:** 0.0.10
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

"All strategies should make some points at least." Auditing every
individual match in a full tournament (not just leaderboard totals)
found three distinct causes behind widespread 0-point matches — a
guaranteed-zero starter strategy, a real engine bug where a player's
spawn point could be placed on an impassable cell, and a position
heuristic bug in `example_strategy_v2.py` not caught in v0.0.8 because
that file was deliberately left untouched then. All three fixed; the
only zero-point matches left are real losses to `example_combat`,
confirmed as the `defend()`/attack mechanic working as designed, not a
bug — reported, not changed.

## Fixed

**`SimulationCore._default_injection_point()` could return an
impassable cell, permanently trapping a player's NanoAI.** Confirmed on
`maps/vascular_network.json`: player 0's injection zone is `(0,0)-
(4,4)`, fully passable except for a Bone border that happens to seal
exactly the `(0, 0)` corner — and `_default_injection_point()` blindly
returned that literal corner with no passability check. Both cardinal
neighbors of `(0, 0)` are also Bone (the whole border row/column is),
so there was no path out at all — not something any strategy, however
written, could route around. Confirmed identical in the Godot original
(`simulation_core.gd`'s `_default_injection_point()`), not a Python-port
regression. Now searches the rest of the zone for any passable cell
before falling back to the literal corner, which is only used as a last
resort if the entire zone is impassable. 3 new tests.

**`example_strategy.py` was guaranteed to score 0 in every match**,
structurally — it moved bots toward a Habitas Point but never built a
needle. Rewritten to actually plant an (empty, AZN-less) needle on the
nearest unoccupied point once adjacent — still far simpler than
`example_strategy_v2.py` (no collector, no AZN economy), but now a real,
if minimal, scoring strategy rather than a guaranteed loss.

**`example_strategy_v2.py` measured "nearest Habitas Point" from a
hardcoded `(0, 0)`** instead of the bot's own actual position — the same
bug found and fixed in all six new v0.0.8 strategies, but `v2` was
explicitly left out at the time as an "existing, already-shipped
reference strategy, out of scope." This round's "all strategies" framing
includes it. Fixed the same way, plus added the same "boxed in, move
toward the target instead of sitting frozen" fallback the other six
files already had.

## Verification

Per-strategy count of matches scoring exactly 0, across a full clean
56-match tournament, before and after this version's fixes:

| Strategy | Before | After |
|---|---|---|
| `example_strategy` | 14/14 | 2/14 |
| `example_container` | 7/14 | 2/14 |
| `example_combat` | 7/14 | 0/14 |
| `example_defense` | 6/14 | 2/14 |
| `example_explorer` | 5/14 | 2/14 |
| `example_full_roster` | 4/14 | 2/14 |
| `example_ip_creator` | 3/14 | 2/14 |
| `example_strategy_v2` | 2/14 | 2/14 |

Every remaining 2/14 individually checked against its actual replay
file and confirmed to be a real combat kill by `example_combat` (the
opponent's NanoAI/needle alive-status reads `False` in the final
frame), not a recurrence of any of the three fixed causes.

```
$ pytest tests/
299 passed in 1.01s

$ python tests/check_editor.py
ALL OK
```

## Found, not fixed

**`example_combat` shuts its opponents out completely (0 points) in
every one of its matches**, and `example_defense`'s NanoBlocker/NanoWall
don't help against it — both only block *movement* through their own
cell, which does nothing against `defend()`'s ranged attack from up to
12 cells away. This is the attack mechanic working exactly as designed
(confirmed in v0.0.8 too), not a bug. Whether this balance is desirable
— and if not, whether to soften combat or give economic strategies some
other way to resist it — is a design decision, reported here rather than
decided unilaterally, the same way the v0.0.2 tie-break and v0.0.8
contested-Habitas-Point findings were.

## Known gaps carried forward

- The combat-effectiveness/defense-design question above.
- Contested-Habitas-Point scoring resolution (v0.0.8 §6) — still open.
- No unit tests for the pygame rendering/widget layer — unchanged gap
  from every prior version.
