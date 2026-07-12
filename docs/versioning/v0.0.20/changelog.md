# v0.0.20 Changelog

**Version:** 0.0.20
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Fixes every finding from the v0.0.19 UX/QA review ("fix all"). The
two headline repairs stop the app lying to its users: strategy
crashes/timeouts are now narrated on screen instead of dying in the
console, and replays with missing maps announce themselves instead of
silently rendering nonsense. Plus: full replay browsing with cleanup,
type-to-filter file browsing, editor redo, tournament map selection
and list scrolling, a follow camera, clickable event rows, and a
Guide button. 352 tests (+7).

## Fixed — "the app lies to you" class

- **Strategy failures are visible now.** The engine writes
  `strategy_error` (exception type + message) and `strategy_timeout`
  (measured ms) events into the replay; the match window's Events
  panel shows them in warning color the turn they happen. Measured
  before: 1,500 console warnings, zero on-screen signals; after: an
  event every failing turn, collapsed in the timeline so a
  permanently-dead strategy is one story line, not 1500 copies.
- **Missing-map replays announce it**: a red banner ("showing blank
  terrain — bots/objectives are real, walls and streams are not") and
  a "(file missing!)" marker on the HUD map line, instead of bots
  floating on silent blank tissue.
- **Editor status bar** no longer overprints the filename at minimum
  window width (truncates with an ellipsis).
- **Unnormalized `../..` paths** in every UI module's dir constants —
  they leaked into user_prefs and file-equality checks where
  `a/b/../c` != `a/c`. All normpathed.

## Added — viewer

- **Events rows are clickable** — jump straight to that turn (hover
  highlight; header says so).
- **Follow camera**: C keeps the selected bot centered; manual pan or
  F releases it. Hint line updated.
- **Replays… lists everything** (was newest-14 of 88), scrollable
  with a proportional scrollbar, and each row has an [x] that deletes
  the replay file and keeps the modal open for batch cleanup.

## Added — everywhere else

- **File browser**: type-to-filter (substring; first Esc clears the
  filter, second closes) + scrollbar.
- **Editor redo**: Ctrl+Y / Ctrl+Shift+Z + a sidebar Undo|Redo row.
  Implementation note: the history stack stores pre-mutation
  snapshots, so the post-edit state exists nowhere in it — undo()
  captures it into a redo stack at the only moment it's both current
  and about to be lost; save_state() clears the branch; the position
  index moves in lockstep so dirty tracking stays exact. +4 tests.
- **Tournament**: "Maps…" multi-select chooses which maps the
  round-robin runs on (default: all shipped; button shows the count;
  setup screen names them); competitor lists window to 8 rows with
  wheel scrolling.
- **Main menu**: a **Guide** button opens the participant guide in
  the system browser — the guide was previously only discoverable by
  browsing the repo.

## Deliberately left open

- **SCO-03** (per-map bonus objectives): a scoring-design decision,
  not a fix — the only remaining M7 item, awaiting the user's call.

## Verification

```
$ pytest tests/                 -> 352 passed (+3 strategy events, +4 redo)
$ python tests/check_editor.py  -> ALL OK
31-check interaction harness, all pass — includes: 40/40 failing turns
  emit events; ticker collapses them; ticker click jumps to the turn;
  C follows / pan releases; ghost-map banner; picker lists all 87
  replays and its [x] really deletes a file; filter narrows /usr/lib
  200 -> 2; Ctrl+Z/Ctrl+Y round-trip a paint; tournament windows to 8
  rows, scrolls, and runs on a chosen map subset; Guide button opens
  the right file; 5-button menu fits at 1024x640.
Screenshots inspected: crash ticker (red line + jump header),
  missing-map banner, tournament scroll + maps selection, truncated
  editor status bar.
```
