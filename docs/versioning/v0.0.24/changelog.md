# v0.0.24 Changelog

**Version:** 0.0.24
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Rebalances the demo tournament without changing any game rule: the
passive economy strategies now defend their needle, so pure aggression
(`example_combat`) is no longer undefeated. Combat fell from **14–0 to
12–2 and off the top of the leaderboard** — a balanced economy
strategy is now the champion. No engine, scoring, or stat change (the
collector's economy+attack dual role is canon to the original, and
wins stay the championship metric).

## Why (measured)

Combat's 14–0 survived every stat/scoring lever — needle HP to 500,
collector range/damage cuts, an unkillable AI, cumulative scoring — all
left it at 13–14. The real cause: combat *hunts and eliminates*
(15/56 matches ended by ~turn 275 with the loser wiped out), and the
economy demos never defended. Head-to-head isolation showed only the
full **watchtower + reactive wall + shoot-back** reflex flips a passive
economy strategy from **0/24 to 17/24 vs combat** — the three pieces
are synergistic; none works alone.

## Added

- **`nanobot/api/reactive_defense.py`** — `ReactiveDefenseMixin`, a
  reusable three-part reflex (`run_defense_ai` = watchtower explorer +
  reactive wall + garrison; `park_watchtower`; `shoot_back`) with
  self-contained geometry. Lives in the package so the strategy loader
  never mistakes it for a competitor.

## Changed — strategies

- **`example_strategy_v2`, `example_container`, `example_ip_creator`**
  now inherit `ReactiveDefenseMixin` and defend their needle once it's
  built. Untouched: `example_combat` (aggressor), `example_defense`
  (already defensive, the reference this distills), `example_explorer`
  (competitive speed-demo), `example_full_roster` (own defense),
  `example_strategy` (minimal starter — separate concern).

## Result (56-match tournament, leaderboard order)

```
1  strategy_v2  12W  2L  2560 pts   <- balanced economy is champion
2  combat       12W  2L  1600 pts   <- was 14-0; now tied, out-scored 60%
3  ip_creator   11W  3L  2280 pts   (was 7W)
4  explorer      9W  5L  2170 pts
5  defense       5W  8L  1970 pts
6  container     3W 11L  1175 pts   (relay keeps its collector off the needle)
7  full_roster   3W 10L  1440 pts
8  strategy      0W 14L   130 pts   (minimal starter — fix #4, not taken yet)
```

Early eliminations fell 15→11. Zero-score cases are all combat
matches (the aggressor eliminating opponents) — the v0.0.10 invariant
holds.

## Verification

```
$ pytest tests/                 -> 362 passed
$ python tests/check_editor.py  -> ALL OK
Loader check: each edited demo instantiates its own ExampleXxx class;
  the imported mixin is correctly not treated as a strategy.
```

## Known limits carried forward

- `container` stays low (3W): its mid-map relay keeps the collector
  away from the needle, so `shoot_back` rarely fires — the watchtower +
  wall extend survival but can't win a duel the collector isn't present
  for. A structural property of the relay pattern, not a bug.
- `example_strategy` (0W) is the minimal starter — the deliberately
  separate fix #4 (buff the starter), which the user has not yet taken.
