# v0.0.21 Changelog

**Version:** 0.0.21
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Implements SCO-03 per the user's "per map" decision: a per-map
**hold-all bonus** — extra points every turn while a single player
holds every Habitas Point. With it, **every planned milestone
(M1–M7) is complete**. 362 tests (+10).

## Added

- **`bonus_hold_all`** map field (0/absent = off): parsed clamped ≥0,
  serialized only when set, undo-snapshotted in the editor, validated
  by round-trip tests.
- **Engine rule**: `_update_scores` grants the bonus when the
  owner-set of all habitas points is exactly one real player.
  Stateless like all scoring — a needle dying drops the bonus the
  same turn (tested: earned / partial / split / vanishes-on-death /
  zero-bonus / no-habitas).
- **`map_info.bonus_hold_all`** for strategies, documented in the
  guide's API table.
- **Editor "Map Settings"**: the Starting-AZN section became two
  labeled stepper rows — AZN (±25) and Bonus (±10, "off" at 0, green
  when set). Undoable, dirty-tracked, sidebar still fits the 1024×640
  minimum (bottom = 632).
- **HUD**: bonus maps show "Hold all N points: +B/turn", flipping to
  "P2 collecting +50/turn!" in the holder's color while it's live.
  Maps without a bonus reserve no space.
- **Heart Chambers ships with +50** — full control of its five points
  (center prize included) is now worth double a bare five-needle
  spread, on the map whose whole design is about the contested
  center.

## Verification

```
$ pytest tests/                 -> 362 passed (+6 engine, +4 loader)
$ python tests/check_editor.py  -> ALL OK
Interaction script: stepper +/- and undo, dirty tracking, min-height
  fit, heart_chambers loads at 50, HUD line present on bonus maps and
  absent otherwise, collecting highlight renders in player color.
Balance: 28-match Heart Chambers round-robin with the bonus live —
  standings healthy (explorer 1300 ... starter 55, everyone scores)
  and the bonus fired on zero turns: no demo strategy ever holds all
  five points, so it's a pure strategic carrot that changes what a
  future strategy could go for without moving today's balance.
Screenshots inspected: editor Map Settings, HUD idle + collecting.
```

## Roadmap state

M1–M7: all ✅. The requirements sheet has no open items — future
versions are new scope, not debt.
