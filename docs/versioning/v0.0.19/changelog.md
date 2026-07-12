# v0.0.19 Changelog

**Version:** 0.0.19
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

The map creator is complete: it can now author **everything a map
file can express** — closing MAP-08, the oldest open requirement.
White-cell patrols get a real tool, maps can be created at any size,
the starting AZN budget is editable, saves validate placement sanity
and name themselves properly, and the participant guide finally has a
map-making chapter. 345 tests (+15).

## Added — editor

- **White Cell tool** (Elements row): click passable cells to lay a
  patrol route — live numbered green preview — then right-click or
  Enter to commit (a single waypoint makes a stationary guard).
  Backspace removes the last pending point; keys **1/2/3** set the
  patrol's speed (a step every 1/2/3 turns); right-clicking an
  existing patrol's waypoint deletes that patrol. Impassable cells
  are refused with a status-bar explanation. Stats default to the
  shipped maps' proven values (hp 45 / damage 3 / range 1.5); the
  guide documents the JSON escape hatch for rare fine-tuning.
- **New Map**: size dialog (e.g. `60x60`, clamped 10–200 per side),
  guarded by the same unsaved-changes confirmation as Load. Garbage
  input gets a friendly message, not a crash.
- **Starting AZN stepper** (sidebar): −25/+25 around the displayed
  budget — a real, undoable document edit. The field had round-tripped
  since v0.0.2 with no way to change it from the UI.

## Fixed

- **Clear Map leaked hazards**: `clear_all()` cleared every element
  list except patrols, which silently survived into the next save.
- **Every new map saved as "Untitled Map"**: the display name is the
  replay→map resolution key, so duplicates made replays ambiguous.
  Saves now stamp a filename-derived name (`marrow_gauntlet.json` →
  "Marrow Gauntlet").
- **validate() ignored placement sanity**: objectives on Bone, fully
  boned injection zones, and boned patrol waypoints now fail
  validation (surfaced by the existing save-anyway dialog) instead of
  producing broken matches.

## Added — docs

- **Guide section 10, "Creating your own maps"**: full tool table
  (including the previously undocumented Edit+Enter AZN-quantity
  entry, Ctrl+Z/Ctrl+S, middle-drag pan), map-design guidance
  (mirrored spawns, reachability, chokepoints, patrols as pressure),
  authored-patrol stat defaults + JSON tuning, and the save/play loop
  with headless side-swap balance testing. TOC updated; MAP-08 ✅ in
  requirements (M7's last item is now the SCO-03 decision).

## Verification

```
$ pytest tests/                 -> 345 passed (+15)
$ python tests/check_editor.py  -> ALL OK
Interaction script: 26 checks, all pass — sidebar button activates
  tool; waypoints via real clicks; bone refusal; speed key; commit;
  Ctrl+Z removes patrol; right-click deletes committed patrol; AZN
  stepper +25 and undo; dirty-guarded New; 30x40 creation; bad size
  spec -> message; save derives "Qa Temp Map" + tracks file + marks
  clean; hazards round-trip editor save/load; validation surfaces in
  the save flow; sidebar bottom=602 at the 640px minimum.
Screenshots inspected: pending-path preview + new sidebar (Starting
  AZN row, New/Load row, white-cell button active), New Map dialog,
  editor at 1024x640.
Guide HTML: tag-balance clean.
```

## Known gaps carried forward

- SCO-03 (per-map bonus objectives) — the last open M7 decision.
- Per-patrol stat editing UI and committed-waypoint editing —
  deliberate non-goals (see plan.md).
