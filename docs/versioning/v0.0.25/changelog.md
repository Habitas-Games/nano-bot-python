# v0.0.25 Changelog

**Version:** 0.0.25
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Actually dethrones combat, and corrects v0.0.24's over-claim. v0.0.24
said combat was off the top; the user's real app tournament showed it
still #1 at 13–1. v0.0.24's probe was wrong two ways (different seeds,
and comparing scores instead of the app's `winner_id` tiebreak). Fixed
here with app-faithful measurement — and a real bug in the defense
specialist. **Result: `example_defense` is now champion (12W), combat
is #2 (11W).**

## Fixed

- **`example_defense` lost to combat 0/24** despite being the defense
  specialist. Two bugs: (1) it never shot back (watchtower + wall alone
  is measured at 0/24 vs combat — the pieces only work together), and
  (2) its war-chest banking sent the collector to spawn, so it was
  never positioned to shoot the raider and the needle starved (219
  attacks, 0 blocked, needle dead by turn 300 in the trace). Now it
  inherits `ReactiveDefenseMixin` for shoot-back and keeps its
  collector home to feed the needle (reactive walls fund from the
  starting 150-AZN bank). Defense now beats combat **20–12**
  head-to-head.
- **`example_ip_creator`** builds its watchtower before expanding
  (via the new `needs_defense` helper), so its defense is up before
  the raid instead of after.

## Added

- `ReactiveDefenseMixin.needs_defense(map_info, my_bots, needle)` —
  True while the needle lacks a watchtower or a raider is closing;
  lets a strategy prioritise defense over the rest of its build order.

## Result (app-faithful tournament, winner_id, seed 0–55)

```
1  defense      12W  2L  2650 pts   <- defense specialist is champion
2  combat       11W  3L  1860 pts   <- was 13-1 (#1); now #2
3  strategy_v2  10W  4L  2490 pts
4  ip_creator    9W  5L  2040 pts
5  explorer      8W  6L  2110 pts
6  full_roster   3W 11L  1380 pts
7  container     3W 11L  1175 pts
8  strategy      0W 14L   125 pts
```

Combat fell 14→13→11 across the two rebalances and is no longer the
champion. Top five within four wins.

## Correction to v0.0.24

v0.0.24's leaderboard ("strategy_v2 #1, combat #2") came from a probe
using non-app seeds and a score-comparison winner rule. The real app
result after v0.0.24 was combat #1 at 13–1. This version measures
app-faithfully (`winner_id`, exact schedule) and reproduces the user's
numbers, then fixes it for real.

## Known limits carried forward

- `container`, `full_roster`, `example_strategy` stay low — structural
  to what each demonstrates (relay keeps the collector off the needle;
  two spread needles; minimal starter). Not bugs. The starter is
  still the untaken fix #4.

## Verification

```
$ pytest tests/                 -> 362 passed
$ python tests/check_editor.py  -> ALL OK
Loader: each edited demo instantiates its own class.
Measurement app-faithful; reproduces the reported combat-#1 pre-fix.
```
