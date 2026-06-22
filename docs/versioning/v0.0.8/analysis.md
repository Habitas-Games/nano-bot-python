# v0.0.8 — Engine Fixes & Full Strategy Roster Analysis

**Status:** Complete
**Depends on:** [../v0.0.7/changelog.md](../v0.0.7/changelog.md)

---

## 1. Trigger

"I want to have more strategies that use the rest of the bots and
resources." Only two example strategies existed
(`example_strategy.py`, a naive starter; `example_strategy_v2.py`,
which uses NanoAI/NanoCollector/NanoNeedle) — five bot types
(NanoExplorer, NanoContainer, NanoIPCreator, NanoBlocker, NanoWall) and
two mechanics (defend()/attack, multi-point claiming) had no
demonstration at all. User's choice on structure: several focused
single-mechanic demos plus one comprehensive combined strategy.

## 2. Found before writing anything: three bots were silently non-functional

Verifying each remaining bot's mechanic against the actual code (not
assuming the participant guide's own descriptions were accurate — they
were ported faithfully from Godot in v0.0.6, including whatever the
original got wrong) surfaced three real gaps, each confirmed two ways:
reading the relevant `simulation_core.py`/`map_data.py` code, then
directly executing it and checking the result.

- **NanoContainer couldn't receive or hold AZN at all.**
  `_action_transfer`'s target search only ever matched `bot.type ==
  "NanoNeedle"` — a `NanoContainer` standing anywhere a collector tried
  to deliver to was simply never found as a valid target. "High-capacity
  storage for long supply chains" (the bot's own flavor text, ported
  unchanged from Godot) was unreachable.
- **NanoExplorer's density immunity didn't affect movement cost.**
  `density_immune` was read onto the bot (`nanobot_data.py`) with a
  comment crediting it to NanoExplorer, but the only place it was
  actually checked was to exempt it from `NanoBlocker`'s traversal
  penalty — `MapData.movement_cost()` had no parameter for it at all, so
  an explorer paid the exact same 2/3/4 density-tier cost as any other
  bot. Confirmed directly: moved an immune and a non-immune bot into an
  identical HIGH-density cell and compared `turns_until_move` — both
  came out to 4.
- **NanoIPCreator's `open_ip()` only logged an event.** It never touched
  `self._map.injection_zones` or anything else `_is_at_injection_point`
  checks, so "creates a new injection point" had zero gameplay effect —
  a bot standing on the supposedly-new point still couldn't bank AZN
  there.

All three are confirmed identical in the Godot original
(`simulation_core.gd`, `grid_pathfinder.gd`, `nanobot_data.gd`) — none
are Python-port regressions. Per the user's explicit choice (asked
directly, since fixing match-affecting engine behavior crossed from
"bug fix" into "product decision" the same way the v0.0.2 tie-break
finding did): fix all three, then build the new demos around mechanics
that actually work.

## 3. Fixes

- `MapData.movement_cost()` gained a `density_immune` parameter (default
  `False`) that substitutes `MIN_MOVE_COST` for the density-tier cost —
  Bone stays impassable regardless (a structural barrier, not a density
  tier), and bloodstream bonus/penalty still applies on top, unchanged.
  Threaded through `GridPathfinder.find_path()`/`path_cost()` too,
  otherwise an immune bot's *cost* was fixed but the *path it actually
  chose* still optimized for a cost it no longer paid, detouring around
  terrain it could now cross for free.
- `SimulationCore._action_transfer()`'s target search now accepts any
  alive friendly bot with `capacity > 0` (the same criterion
  `_action_collect()` already used to decide which bot types can hold
  AZN at all, so this isn't a new rule — it's the existing one applied
  consistently) instead of hardcoding `"NanoNeedle"`. Needed an explicit
  `target is bot` exclusion: NanoCollector and NanoContainer both have
  `capacity > 0` *and* `transfer > 0` (unlike NanoNeedle, whose
  `transfer` is 0), so without the exclusion a bot banking AZN at its
  own position could match itself as the "target" and silently no-op
  instead of reaching the actual bank-deposit fallback. Caught by 4
  existing tests failing immediately after the first version of this
  fix — confirmed which side was wrong (the fix, not the tests) before
  changing either.
- `SimulationCore._action_open_ip()` now appends a real `{"player":
  ..., "rect": (x, y, 1, 1)}` zone to a new per-match
  `self._injection_zones` list (seeded from `self._map.injection_zones`
  at match start, not the map object itself — the map can be reused
  across tournament matches and shouldn't accumulate one match's IP
  creations into the next) instead of only emitting an event. Guarded
  against creating a duplicate zone if a strategy calls `open_ip()`
  repeatedly from the same spot, since "re-issue the same command every
  turn" is the idiom the rest of this API already encourages for
  `move_to()`. `_is_at_injection_point`, `_choose_injection_point`, and
  `_default_injection_point` all read from this new list now.

## 4. Building the demos surfaced two more real bugs, both caught by execution

- **`example_explorer.py`'s explorer oscillated instead of parking.**
  Recomputing "farthest Habitas Point from current position" every time
  the explorer had no queued path meant that once it *arrived* at the
  original farthest point, the same calculation — now run from way out
  there — picked a new farthest point back near the start, sending it
  walking all the way back, then all the way out again, forever.
  Confirmed by running a real match and checking the explorer's final
  position: it ended up stranded mid-map, nowhere near either end.
  Fixed by deciding the target once and storing it on the strategy
  instance, never recomputing.
- **`example_full_roster.py`'s expansion was permanently unfunded.**
  Three compounding causes, found by tracing one real match step by
  step: (1) the collector feeding the first needle never banked any
  AZN — once a needle accepts a delivery it always returns immediately
  inside `_action_transfer`'s loop, so a collector that only ever
  targets the needle never reaches the bank-deposit fallback, capping
  the team's build budget at whatever was left of the starting 150 after
  the first few builds, forever; (2) once that was fixed, a second issue
  surfaced — the delivery condition re-checked the same `azn >= 10`
  threshold used to decide whether to *leave* a node to decide whether
  to *finish* a delivery already in progress, so a collector banking
  from far away abandoned the trip the instant the 5/turn transfer rate
  dragged it under 10, going back for a small top-up instead of finishing
  the drop-off — turning each "deliver everything" trip into a much less
  efficient "deliver a little, then leave with the rest still on board";
  (3) NanoWall's ~50-turn auto-destruct meant unconditionally rebuilding
  it forever consumed AZN faster than the now-working economy could
  replace it, permanently starving every other build. Fixed by banking
  surplus once the first needle hits a funding cap, fixing the delivery
  priority to always finish a delivery already at its target before
  reconsidering, and capping wall rebuilds instead of maintaining it
  indefinitely.

## 5. A correctness issue found by testing every strategy in both player slots

Every new strategy's "nearest Habitas Point" calculation measured
distance from a hardcoded `(0, 0)` — matching `example_strategy_v2.py`'s
existing pattern, which was assumed safe to copy since it's the
established reference. Testing each new strategy as **player 1** instead
of player 0 (since the playback viewer's picker, built in v0.0.5, lets a
user freely assign any strategy to either slot) showed this was wrong:
`choose_injection_point()` requesting `(0, 0)` only resolves there for
whichever player's actual zone happens to contain it; running as player
1 spawned the NanoAI at a completely different corner (`(75, 75)` on the
map used for testing), and every "nearest" calculation kept measuring
from world-origin `(0, 0)` regardless — sending the strategy after the
*farthest* point instead of the nearest one. Fixed by measuring from
each bot's own actual position (`nano_ai.position`, captured once for
`example_full_roster.py`'s "spawn" reference since `nano_ai.position`
itself changes as it moves) in all six new files. Not changed in
`example_strategy_v2.py` itself — that file is an existing, already-
shipped reference strategy used throughout this project's history as a
trusted baseline opponent; changing its behavior is out of scope here.

## 6. A platform behavior discovered, not fixed: contested Habitas Points

Testing `example_full_roster.py` against `example_strategy_v2.py`
surfaced a case where both players' needles ended up on the *same*
Habitas Point (a coincidence of this particular map's symmetry, not a
heuristic bug — confirmed after the position fix above, both players'
own-spawn-relative "second nearest" calculations legitimately agreed on
the same point). `_update_scores()` resets every point's owner each
turn and then re-derives it by iterating `self._bots` and overwriting
unconditionally on any position match — so whichever needle appears
*later* in that list (correlating with build order) claims the entire
point's score every turn, while the earlier needle's identical
investment (confirmed: 55 AZN sitting in a fully-alive, full-HP needle)
contributes nothing at all. Not "split," not "first claim holds" — total
silent transfer of one side's score to the other every single turn.

This is reported here as a discovered fact about the platform, not
fixed: contesting a point at all (two needles able to occupy one cell
simultaneously, with no exclusivity check at build time) might be
intentional design, and changing the resolution rule changes match
outcomes the same way the v0.0.2 tie-break did — exactly the kind of
thing to flag rather than silently decide.
