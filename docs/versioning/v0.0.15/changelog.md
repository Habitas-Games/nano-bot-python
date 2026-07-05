# v0.0.15 Changelog

**Version:** 0.0.15
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Full UX/QA review of all four screens, executed with a headless
screenshot-and-events harness. Nine confirmed defects fixed (screenshot
or scripted-interaction evidence for each, before and after) and a
usability pass on the biggest friction points: the match window now
opens fitted and playing with cursor-anchored zoom and real keyboard
control, the tournament shows live standings and can be re-run, and the
editor stops losing work silently. 321 tests (+2).

## Fixed — verified defects

- **Viewer**: match status / "Simulating…" spinner drew directly over
  the Replays…/Seed buttons after every restart (anchor predated those
  buttons). Status now has its own full-width strip under the top bar.
- **Viewer**: Events ticker overlapped the Bot Inspector at small
  window heights; rows now clip to the space above the inspector.
- **Viewer**: the two v0.0.14 tooltips never rendered — tooltip drawing
  existed only inside the editor sidebar. Promoted to a shared
  `draw_hover_tooltips` widget helper used by both screens.
- **Main menu**: Quit clipped off-screen below ~660px height; the
  button stack now clamps to the window bottom (subtitle anchored to
  it), and the window itself clamps to 1024×640 minimum.
- **Tournament**: leaderboard "aligned" with f-string padding in a
  proportional font — ragged everywhere. Now fixed-pixel columns.
- **Tournament**: could never be re-run (started-flag never reset);
  Start becomes "Run Again" when finished.
- **Editor**: Undo button never enabled from actual editing (no tool
  called `set_undo_enabled`); state now synced every frame in draw().
- **Editor**: Save prefilled `my_map.json` regardless of what was
  loaded; now prefills the current file's name.
- **Editor**: Load silently discarded unsaved edits; now tracks
  dirtiness (undo-stack position vs last save/load — undoing back to
  the saved state correctly counts as clean) and asks first.

## Improved — usability

- **Viewer**: opens fitted-to-window, centered, and auto-playing on
  every load path; wheel zoom anchors at the cursor (multiplicative
  steps); panning is clamped so the map can't be lost; `F` re-fits;
  Home/End jump to the ends; held arrows repeat (key repeat is on
  app-wide); speeds extended to 8×/16×; a hint line in the top bar
  makes all of it discoverable.
- **Seeds in replays**: `MatchLog.seed` (backwards compatible — old
  replays load as None and honestly show "Seed —"), so any opened
  replay can be rerun exactly via the existing lock toggle.
- **Replays… picker** shows each file's age; the picker modal sizes to
  its labels.
- **Run Match default**: prefers example_explorer vs example_defense
  (200-170 over the full 1500 turns in the end-to-end check) over the
  alphabetical example_combat vs example_container (70-0 stomp in 287
  turns) — first impressions matter.
- **Tournament**: live standings while running, podium colors on the
  top 3 (closes TRN-05), normalized results path.
- **Editor**: middle-drag pans from any tool; Ctrl+Z / Ctrl+S;
  cursor-anchored wheel zoom; top bar shows the current filename with
  an "* unsaved" marker; Load/Save/Clear/Undo have tooltips.

## Verification

```
$ pytest tests/                 -> 321 passed (+2: seed round-trip, missing-seed default)
$ python tests/check_editor.py  -> ALL OK
QA harness: 19 behavioral checks + 10 screenshots -> all pass
End-to-end: menu -> Run Match (real sim) -> viewer auto-playing,
  explorer vs defense, both players scoring; editor paint -> Undo
  enabled + dirty flag -> confirm-discard on Load -> Ctrl+Z clean
```

- The one deliberate behavior change to watch: `example_combat` vs
  `example_container` is no longer the default first match; nothing
  else about simulation behavior changed (seed field is additive).
- Screenshots inspected before/after for: viewer status strip, small
  (1024×640) viewer, menu at min size, tournament running + finished,
  editor dirty indicator + confirm-discard modal, replay picker with
  ages, tooltip rendering.

## Known gaps carried forward

- Editor hazard authoring tool (MAP-08 🟡); SCO-03 decision.
- The 1024×640 minimum is enforced by re-calling `set_mode` on resize;
  window managers that ignore programmatic resizes may still show a
  smaller window briefly, but layouts remain collision-free at any
  size ≥ the minimum and the ticker clip degrades gracefully below it.
