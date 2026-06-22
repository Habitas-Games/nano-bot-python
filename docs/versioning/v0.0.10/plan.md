# v0.0.10 — Every Strategy Should Score Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Audit before fixing: scan every individual match's actual saved score,
not the aggregated leaderboard, to find every distinct zero-score case
before writing any code. Group the causes (analysis.md §3) and fix each
at the layer where it actually belongs — engine-level for the spawn-
point bug (affects every strategy and every future map), strategy-level
for the position heuristic and the non-scoring starter.

## Order

1. Full 8-strategy tournament, then a script scanning every saved
   replay's `final_scores` for exact zeros, broken down per strategy.
2. For each strategy with a 0, find one concrete match and trace the
   actual cause from the replay's final frame — bot positions, alive
   status, AZN carried — before writing any fix.
3. Fix `SimulationCore._default_injection_point()`: search the zone for
   any passable cell instead of blindly trusting the rect's corner, only
   falling back to the corner if the entire zone is impassable. Added 3
   tests: the confirmed scenario, a no-regression case (passable corner
   still used as-is), and the fully-impassable-zone fallback.
4. Apply the same "nearest Habitas Point from the bot's own position"
   fix already used in v0.0.8's six new files to `example_strategy_v2.py`
   too, plus the same boxed-in movement fallback.
5. Rewrite `example_strategy.py` to actually plant a needle (still far
   simpler than `example_strategy_v2.py` — no collector, no AZN economy,
   just claim a point) instead of only ever walking toward one.
6. Re-run the full tournament and re-scan for zeros; confirm every
   remaining case is specifically a loss to `example_combat`, then trace
   one to confirm it's a real kill, not a different bug wearing the same
   symptom.
7. Full regression sweep (pytest, `tests/check_editor.py`).

## Verification

```
$ pytest tests/
299 passed in 1.01s

$ python tests/check_editor.py
ALL OK
```

Per-strategy zero-score count across a full clean 56-match tournament,
before and after:

| Strategy | Before | After |
|---|---|---|
| example_strategy | 14/14 | 2/14 |
| example_container | 7/14 | 2/14 |
| example_combat | 7/14 | 0/14 |
| example_defense | 6/14 | 2/14 |
| example_explorer | 5/14 | 2/14 |
| example_full_roster | 4/14 | 2/14 |
| example_ip_creator | 3/14 | 2/14 |
| example_strategy_v2 | 2/14 | 2/14 |

Every remaining 2/14 confirmed (by checking the actual replay) to be a
loss specifically to `example_combat`, not a recurrence of any of the
three fixed causes.

## Explicit non-goals for this version

- Not changing `example_combat`'s effectiveness or giving the economic
  strategies a defense against ranged attack — analysis.md §4, a
  balance decision reported rather than made unilaterally.
- Not changing the contested-Habitas-Point scoring behavior found in
  v0.0.8 — still open, still not part of what was asked this round.
- Not updating the illustrative code snippets in `README.md` or
  `docs/participant_guide.html` — those are syntax illustrations meant
  to be edited, not strategies that actually get loaded and run; only
  the real, executable `strategies/*.py` files are in scope for "all
  strategies should score."
