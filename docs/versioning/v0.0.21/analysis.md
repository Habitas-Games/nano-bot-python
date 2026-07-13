# v0.0.21 — SCO-03 Hold-All Bonus Analysis

**Status:** Complete
**Depends on:** [../v0.0.20/changelog.md](../v0.0.20/changelog.md)

---

## 1. Trigger

SCO-03 ("optional per-map bonus objectives, e.g. +50 for holding all
points") was the last open roadmap item, presented to the user as an
implement-or-drop decision. Answer: "per map" — implement it as a
per-map configuration.

## 2. Design: one objective type, done well

The shipped form is exactly the requirement's own example: a per-map
integer `bonus_hold_all` — extra points **per turn while a single
player holds every Habitas Point** (0/absent = no bonus).

Why only the hold-all form, and why per-turn rather than one-time:

- **Stateless by construction.** The engine's scoring is recomputed
  from live state every turn (a destroyed needle's income vanishes
  immediately). A "while true" bonus slots into `_update_scores` in
  five lines with no new state, no award tracking, and no edge cases
  around needles dying and points reopening. One-time awards would
  need persistent accumulators — a different scoring model entirely.
- **It's the interesting one.** Holding all N points simultaneously is
  the natural "domination" objective; it directly rewards the playstyle
  the maps' contested centers already gesture at. More exotic types
  (first-to-X, zone control, kill bounties) can wait until an actual
  map design wants one — the JSON field pattern generalizes when
  needed. Recorded as Revision 5 in the requirement.
- **MAP-08 stays true**: the editor must author everything a map JSON
  expresses, so the field gets a stepper — the "Starting AZN" section
  became a two-row "Map Settings" section (AZN / Bonus), which also
  reclaimed a header and keeps the sidebar under the 640px minimum
  (bottom = 632).

## 3. Where it surfaces

- **Engine**: `_update_scores` adds the bonus when the owner-set of
  all habitas points is exactly one real player. 6 tests (earned,
  partial, split, vanishes-on-death, zero-bonus, no-habitas).
- **Strategies**: `map_info.bonus_hold_all` — a strategy can decide
  whether full-map aggression is worth it on this map.
- **Spectators**: the HUD shows "Hold all N points: +B/turn" on bonus
  maps, switching to "P2 collecting +50/turn!" in the holder's color
  the moment it's live.
- **Authors**: editor stepper (+/-10, "off" at 0, undoable,
  dirty-tracked), guide sections (§6 Scoring, §10 Map Settings), API
  table row.
- **Content**: Heart Chambers ships with **+50** — its contested
  central chamber already makes full control the map's theme.

## 4. Balance check

28-match round-robin on Heart Chambers with the bonus live: standings
healthy (explorer 1300 pts … starter 55), every strategy scores, and
the bonus fired on **zero** turns — no demo strategy ever holds all
five points. The bonus is a pure strategic carrot: it changes what a
future strategy *could* go for without moving today's balance at all.
(That also means: existing replays, tournaments, and expectations are
undisturbed.)

## 5. Verified

362 unit tests (+10: 6 engine, 4 loader); check_editor ALL OK;
interaction script (stepper +/-, undo, dirty, min-height fit,
heart_chambers loads at 50, HUD line present on bonus maps and absent
otherwise, collecting-highlight render); screenshots inspected
(editor Map Settings, HUD idle line, HUD collecting line in player
color); 28-match balance run.
