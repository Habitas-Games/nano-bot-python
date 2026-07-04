# v0.0.14 Changelog

**Version:** 0.0.14
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Implements the entire v0.0.13 roadmap — M6 "Make it a game" (fog of
war, immune-system hazards, line-of-sight combat, habitas exclusivity,
a third map) and the M7 UX items (replay browser, seed control, event
VFX + ticker, menu art, editor zone-owner selector). The game now has
hidden information, PvE pressure, real counterplay against ranged
attack, and a replay viewer that narrates what's happening. 18 new
tests (319 total).

## Added — gameplay (engine)

- **Fog of war (GAME-01)**: `map_info.visible_enemies` and the new
  `map_info.hazards` contain only what's inside some alive friendly
  bot's scan radius (Euclidean; floor 2 so no bot is blind to an
  adjacent enemy). Scan is now a real stat; NanoExplorer is the team's
  eyes. Terrain/habitas/AZN stay fully visible (anatomy, not troops).
- **Line-of-sight combat (GAME-03)**: shots are blocked by Bone and by
  alive NanoWalls (either player's) on the firing line; blocked shots
  log `attack_blocked`. Acceptance verified by test: a wall-ringed
  needle takes zero damage from a lone attacker. Collectors can also
  shoot white cells.
- **Habitas exclusivity (GAME-04)**: building a needle on a cell with a
  living needle fails (`habitas_occupied`); first claim holds until the
  needle dies. Closes the v0.0.8 contested-point silent-theft finding.
- **White-cell hazards (GAME-02)**: maps declare patrols (looping path,
  HP, damage, contact range, speed). They step every `move_every`
  turns, are blocked by walls/Bone and slowed by blockers, and bite the
  nearest bot of either player in range. Recorded per frame; killable.
- **Death events**: `bot_destroyed` (with cause: attack/hazard),
  `hazard_destroyed`, `hazard_attack` — the replay now contains the
  full story, and the viewer's ticker reads it back.

## Added — content

- **`maps/bone_maze.json`** (GAME-05/MAP-07): 50×50 marrow labyrinth —
  concentric bone rings with offset gaps, two stream arteries, a
  center-prize habitas + four pocket objectives, two patrols. Every
  objective machine-verified reachable from both spawns before shipping.
- **Vascular Network**: two white-cell patrols on verified-passable
  lanes. Simple Tissue stays hazard-free as the beginner map.

## Added — UX (match window, menu, editor)

- **Event VFX + tracers (VIS-08/UX-03)**: gold attack tracers, gray
  blocked-shot tracers, white hazard-bite tracers, and the fx
  animations (impact, build, collect, destruct) at the exact cell —
  looping while a frame is current, so paused/stepped frames are
  self-explanatory.
- **Events ticker**: the HUD lists the last five notable events up to
  the current turn (builds, kills with cause, expiries, new injection
  points) — scrub anywhere and read the story so far.
- **Replays… (UX-01)**: open any saved replay from the match window,
  newest first — tournament and headless runs were previously
  unviewable in-app.
- **Seed control (UX-04)**: Restart rolls a fresh random seed, the seed
  in use is displayed, and a lock toggle reruns the identical match.
  The main menu's first match is random-seeded too (was hardcoded 0).
- **Menu art (UX-03)**: background art (title baked in) with buttons in
  the lower third — repositioned after a screenshot showed the first
  layout overlapping the art's title panel.
- **Editor (MAP-08/UX-02)**: Zone Owner P1/P2 toggle (status bar names
  the owner new zones get); hazard patrol routes render as polylines +
  white blobs so hazard-bearing maps are visible to the creator.
  Hazards also survive editor save (round-trip) and undo (snapshot).

## Changed — strategies (fog/LOS adaptations, all trace-driven)

- **`example_combat`**: artillery + forward observer — an Explorer
  spotter sweeps the enemy's mirror corner; the fighter shadows it
  (a fighter's own scan is ~0 under fog).
- **`example_defense`**: rebuilt around the affordable defense pattern
  found by tracing three failed designs (see analysis.md §3): Explorer
  watchtower on the needle + NanoAI garrison dropping a reactive wall
  on the firing line the turn a raider is spotted (builds resolve
  before attacks). A 60-AZN war-chest cap keeps it scoring in peaceful
  matches — without it a full tournament run showed it hoarding its way
  to 4W-17L; with it, 15W and 3rd place.
- **`example_full_roster`**: its fighter guards the first needle when
  nothing is spotted instead of stopping in the open.

## Verification

```
$ pytest tests/            -> 319 passed
$ python tests/check_editor.py -> ALL OK
Full app flow: menu -> match window with Replays/Seed controls -> OK
```

- **Balance, measured**: defense-vs-combat siege went from "needle dead
  by T630, zero shots blocked" (walls expired before the raid) to
  "needle alive past T1056 with reactive walls" across the traced
  iterations. Final 84-match, 3-map tournament: combat 21W (1830 pts),
  explorer 16W (3060), defense 15W (2810), v2 11W (2820), ip_creator
  10W, container 6W, full_roster 5W, starter 0W (275 — still scores).
  Zero-score scan: only needle-kill sieges zero anyone (~3/21 per
  strategy), preserving the v0.0.10 invariant.
- **Hazards, measured**: 25 hazard attacks in a bone-maze match, 3 on
  vascular — pressure without slaughter; both players scored on both
  maps.
- **Screenshots inspected**: main menu art; editor with bone_maze
  loaded (zone owner P2 active, patrol routes visible); viewer on the
  maze (white cells, ticker, hazard legend, seed/replay buttons);
  viewer on a blocked-shot frame (gray tracer + "shot down" ticker
  lines).
- Docs: requirements statuses flipped (GAME-01..05 ✅, UX-01..04 ✅,
  MAP-07 ✅, G6 ✅; MAP-08 stays 🟡 pending an editor hazard tool);
  participant guide gained fog/white-cell/LOS/exclusivity sections,
  updated turn order, bot cards, demo descriptions, and tips;
  index.html feature cards refreshed; README updated.

## Known gaps carried forward

- Editor hazard authoring tool (MAP-08 🟡) — hazards are JSON-authored.
- TRN-05 top-3 summary view; SCO-03 bonus-objective decision (M7).
- `example_combat` remains unbeaten head-to-head (21W) by design intent
  — counterplay exists and losses are survivable/scoring; revisit only
  if a future strategy meta wants it.
- The cloned `hoshimi-web` repo (outside this project) proved unrelated
  (a same-named TypeScript Lavalink client) and was not used.
