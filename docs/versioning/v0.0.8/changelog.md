# v0.0.8 Changelog

**Version:** 0.0.8
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Six new example strategies covering every bot type and mechanic
`example_strategy_v2.py` didn't touch (NanoExplorer, NanoContainer,
NanoIPCreator, NanoBlocker/NanoWall, defend()/attack), plus a
comprehensive one combining all of them. Before writing any of them,
verified each underlying mechanic actually works — three didn't, and
were fixed with the user's explicit sign-off since the fixes affect
match outcomes. 16 new tests, 296 total.

## Fixed (engine, confirmed inherited from Godot, not Python-port bugs)

**NanoExplorer's density immunity didn't affect movement cost.**
`density_immune` exempted a bot from `NanoBlocker`'s traversal penalty
only — `MapData.movement_cost()` had no way to express it at all, so an
explorer paid the same 2/3/4 density-tier cost as everything else.
Confirmed via direct execution (moved an immune and non-immune bot into
an identical HIGH-density cell, both came out to 4 turns) before fixing.
`movement_cost()` now takes `density_immune: bool = False`, substituting
`MIN_MOVE_COST` for the density-tier cost (Bone stays impassable
regardless; bloodstream bonus/penalty still applies on top). Threaded
through `GridPathfinder.find_path()`/`path_cost()` too — otherwise the
*cost* was fixed but the *route chosen* still optimized for a cost the
bot no longer paid. `SimulationCore._advance_movement()` and
`_action_move()` now pass `bot.density_immune` through to both.

**NanoContainer couldn't receive or hold AZN at all.**
`_action_transfer()`'s target search only ever matched
`bot.type == "NanoNeedle"`. Generalized to any alive friendly bot with
`capacity > 0` — the same criterion `_action_collect()` already uses to
decide which bot types can hold AZN, applied consistently rather than
introducing a new rule. Needed an explicit `target is bot` exclusion:
unlike NanoNeedle (`transfer: 0`), NanoCollector and NanoContainer both
have `capacity > 0` *and* `transfer > 0`, so a bot banking AZN at its
own position could otherwise match itself as the transfer target and
silently no-op. Caught immediately by 4 existing tests failing after the
first version of this fix.

**NanoIPCreator's `open_ip()` only logged an event.** Never touched
anything `_is_at_injection_point()` actually checks, so a newly "created"
injection point couldn't be banked at. `SimulationCore` now tracks
`self._injection_zones` (seeded from the map's static zones at match
start, kept separate from the map object since it may be reused across
tournament matches) and `_action_open_ip()` appends a real
`{"player": ..., "rect": (x, y, 1, 1)}` entry, guarded against
duplicates if a strategy calls it repeatedly from the same spot.
`_is_at_injection_point`, `_choose_injection_point`, and
`_default_injection_point` all read from this list now.

## Added

- **`strategies/example_explorer.py`** — NanoExplorer racing to the
  farthest Habitas Point while the standard collector+needle economy
  runs in parallel; demonstrates the now-fixed density immunity directly
  (verified: 138 turns to cross 137 cells, essentially the theoretical
  minimum).
- **`strategies/example_container.py`** — a NanoContainer relay
  (collector -> container -> needle), verified end-to-end via replay
  events showing both legs of the relay actually firing.
- **`strategies/example_defense.py`** — NanoBlocker + NanoWall on a
  claimed point's chokepoint (closest adjacent cell to the map center),
  with the wall rebuilding after each ~50-turn auto-destruct; verified
  via build-event timestamps 51 turns apart.
- **`strategies/example_combat.py`** — a second collector dedicated to
  hunting visible enemies with `defend()`; verified via attack events
  and a real instance of the fighter wiping out an opponent's entire
  fleet, ending the match early.
- **`strategies/example_ip_creator.py`** — a NanoIPCreator opening a
  forward injection point, with a second collector banking there instead
  of trekking back to spawn; verified via the collector's exact position
  matching the new zone at the moment of each bank event.
- **`strategies/example_full_roster.py`** — all of the above combined:
  two claimed Habitas Points, defense, an explorer-scouted expansion, an
  IP-creator-funded forward base, a container relay, and a dedicated
  fighter, in one strategy.
- 16 new tests: `test_map_data.py` (density-immune movement cost, still
  blocked by Bone, stream interaction preserved), `test_grid_pathfinder.py`
  (density-immune routing actually changes the chosen path, not just the
  cost calculation), `test_simulation_core.py` (NanoContainer
  send/receive, the self-targeting regression, `open_ip()` creating a
  real usable zone, duplicate-call guarding, surviving the creator's own
  death).

## Fixed (in the new strategy files themselves, found while building them)

**`example_explorer.py`'s explorer oscillated back and forth instead of
parking.** Recomputed "farthest point from current position" every time
it had no queued path — once it arrived at the original target, the same
calculation run from out there picked a new farthest point back near the
start. Confirmed via a real match: the explorer ended up stranded
mid-map after 1500 turns. Fixed by deciding the target once, on first
sight of the bot, and storing it on the strategy instance.

**`example_full_roster.py`'s expansion was permanently unfunded**, for
three compounding reasons found by tracing one real match turn-by-turn
(see analysis.md §4 for the full trace): the funding collector never
banked anything (always targeted the needle, which silently no-ops once
it's the matched target regardless of remaining room); the delivery
logic abandoned trips in progress the instant carried AZN dipped under
the same threshold used to decide whether to *start* a trip; and an
unconditionally-rebuilt NanoWall drained AZN faster than the economy
(even once fixed) could replace it. Fixed all three: bank surplus once
the first needle hits a funding cap (30 AZN, baseline 80 pts), always
finish a delivery already at its target before reconsidering whether to
go collect more, and cap wall rebuilds at one extra rather than
maintaining it indefinitely.

**All six new files measured "nearest Habitas Point" from a hardcoded
`(0, 0)`**, copied from `example_strategy_v2.py`'s existing pattern.
Testing each one as player 1 instead of player 0 (not something any
prior test in this project had done) showed the engine assigns each
player's real spawn corner from its own injection zone, not literally
`(0, 0)` — running as player 1 spawned at a completely different corner,
and every "nearest" calculation kept measuring from world-origin
regardless, chasing the *farthest* point instead. Fixed in all six files
by measuring from each bot's own actual position. `example_strategy_v2.py`
itself was not changed — it's an existing, already-shipped reference
strategy, out of scope here.

## Found, not fixed: contested Habitas Points

Two needles from different players can occupy the identical cell (no
exclusivity check at build time), and `_update_scores()` resolves this
by unconditionally overwriting — whichever needle comes later in
`self._bots` (correlating with build order) claims 100% of that point's
score every turn, while the earlier needle's identical, fully-alive
investment contributes nothing. Discovered while testing
`example_full_roster.py`, reported in analysis.md §6, not changed —
deciding the resolution rule changes match outcomes, the same kind of
decision the v0.0.2 tie-break was, and wasn't part of what was asked or
approved this round.

## Changed

- **`README.md`**: lists all six new example strategies under "Writing a
  strategy"; corrected the unit test count (218 -> 296, stale since
  v0.0.2).

## Verification

```
$ pytest tests/
296 passed in 0.76s

$ python tests/check_editor.py
ALL OK

$ python run_tournament.py
# all 8 strategies in strategies/, full round-robin, 56 matches, no crashes
1. example_strategy_v2  — 9W 5L, 2020 pts
2. example_ip_creator   — 9W 5L, 1340 pts
3. example_explorer     — 9W 5L, 1330 pts
4. example_defense      — 9W 5L, 1200 pts
5. example_combat       — 8W 6L,  480 pts
6. example_full_roster  — 7W 7L, 1070 pts
7. example_container    — 5W 9L,  700 pts
8. example_strategy     — 0W 14L,   0 pts   (the deliberately-naive starter)
```

Every one of the six new files also run individually as a real headless
match against both existing reference strategies, **as both player 0
and player 1** — the first time in this project's history any strategy
had been tested in the player-1 slot, which is exactly what surfaced the
position-heuristic bug above.

## Known gaps carried forward

- Contested-Habitas-Point scoring resolution (this version's §6) —
  reported, not fixed, pending a decision.
- No fog-of-war / `visible_enemies` scan-radius limiting — documented as
  a future milestone in `nano_strategy.py` since the original Godot
  port, unrelated to this version's scope.
- No unit tests for the pygame rendering/widget layer — unchanged gap
  from every prior version.
