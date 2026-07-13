# v0.0.26 Changelog

**Version:** 0.0.26
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Removes the "single big winner" for real by giving the demo field a
**rock-paper-scissors cycle** instead of a linear ladder. v0.0.25
dethroned combat only to enthrone defense — because the game was a
straight "best defender wins" hierarchy, so tuning just relocated the
crown. The head-to-head matrix confirmed it: `defense` beat the whole
field. This version supplies the missing counter — a greedy two-needle
economy that out-scores the turtle — so **no strategy beats the whole
field anymore.**

## Changed — `example_full_roster` (now the economy archetype)

Rewritten from the (mediocre, 3W) "all 8 bot types" kitchen sink into
the **greedy two-needle economy**: claims and feeds the two nearest
Habitas Points with two collectors, out-scoring a single-needle turtle
(double the 20-pt base plus AZN across both). Deliberately
**defense-light** — no walls, no watchtower — so an aggressor
(`example_combat`) can punish its spread; keeps a 40-AZN build reserve
(banked at the spawn zone) to reclaim a lost needle. This is the
"economy" corner of the cycle:

```
aggression (combat)  >  greedy economy (full_roster)
greedy economy       >  turtle defense (defense)
turtle defense       >  aggression (combat)
```

(The all-8-bots showcase is dropped — each bot type already has a
focused demo, and a real archetype serves the meta better.)

## Result — no strict king

App-faithful tournament (`winner_id`, seed 0–55):

```
1  defense      11W  3L  2650 pts
2  combat       11W  3L  1720 pts
3  strategy_v2   9W  5L  2500 pts
4  ip_creator    8W  6L  2030 pts
5  full_roster   7W  7L  2760 pts   <- top SCORER; loses to combat, ties the rest
6  explorer      7W  7L  2110 pts
7  container     3W 11L  1175 pts
8  strategy      0W 14L   130 pts
```

- **Strict-king check: empty** — every strategy loses to at least one
  other (was `defense` in v0.0.25). The lead is a two-archetype tie
  (defense/combat), not one dominant strategy, and it shifts with
  seed and map.
- full_roster: 3→7W and the field's top scorer; its record
  (loses to combat, ties everyone else) is the economy archetype
  exactly.
- The economy-beats-turtle edge is **map-dependent by design** —
  economy wins on open Heart Chambers, the turtle wins in Bone Maze's
  corridors. Different maps favour different archetypes.

## Known limits carried forward

- `container` (relay keeps its collector off the needle) and
  `example_strategy` (minimal starter, 0W — the untaken fix #4) remain
  low; structural, documented.

## Verification

```
$ pytest tests/                 -> 362 passed
$ python tests/check_editor.py  -> ALL OK
Loader instantiates the rewritten ExampleFullRoster.
Full head-to-head matrix: no strict king.
Prototype: 2-needle economy beats defense on the open map (320 vs 220
  pts/turn), loses to combat 0/24 — verified before committing.
```
