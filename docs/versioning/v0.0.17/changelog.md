# v0.0.17 Changelog

**Version:** 0.0.17
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

The app stops deciding by folder position and starts remembering the
user's decisions. Run Match no longer auto-simulates the first
map/strategies it finds — the match window opens empty with the last
session's picks restored; map/strategy selection is a real file
browser that can go anywhere on disk and remembers the last folder per
type; and the tournament field is hand-picked (one at a time or
several per browser visit) instead of "everything in strategies/".
330 tests (+9).

## Added

- **`nanobot/core/user_prefs.py`**: `.nanobot_prefs.json` (gitignored)
  remembering exactly four things — last map folder, last strategy
  folder (the two browser defaults), and the last map + strategies run
  (restored across app restarts). Missing/corrupt/unwritable prefs and
  stale paths all degrade to "unset", never to a crash or a fallback
  pick. 9 unit tests.
- **`FileBrowserModal`** (widgets): navigable file browser — folder
  entries + ".." row, extension filter, wheel scrolling, path header;
  single-select mode (click a file to choose) and multi-select mode
  (checkboxes, "Add (n)", Enter confirms). Used by the match window's
  three pickers (single) and the tournament's Add Competitors (multi).

## Changed — match window

- **No autorun**: the menu's Run Match opens the workspace directly;
  the menu's entire background-simulation machinery is deleted. The
  window shows "No match yet — pick a map and both strategies…", the
  action button reads **Run Match** (→ **Restart** once a match is on
  screen), and the turn slider hides until there's something to scrub.
- **No auto-picks, ever**: selectors restore the last session's
  choices where those files still exist; otherwise they read "(pick a
  map)" / "(pick strategy)". The old first-file-in-folder fallbacks
  (menu defaults and the replay-load path) are gone.
- **Browse anywhere**: map/strategy pickers are file browsers starting
  in the last folder used per type (`maps/`/`strategies/` only as
  first-run defaults). Folders persist at pick time; map + strategies
  persist at run time. A non-map .json picked by mistake reports "Not
  a valid map file" instead of a stack trace.

## Changed — tournament

- **Chosen field**: "Add Competitors…" opens the browser in
  multi-select mode — tick one or several and add them in one visit;
  each row has a remove ×; rows from outside `strategies/` show their
  folder; a "N competitors × M maps = K matches" preview replaces the
  old glob. Start gates on ≥2; the field survives Run Again.

## Fixed

- Tournament browser never rendered in the setup phase (the
  not-started draw branch returned before `browser.draw()`) — caught
  by the interaction harness before shipping, restructured so the
  modal always draws last.

## Verification

```
$ pytest tests/            -> 330 passed (+9 user_prefs)
$ python tests/check_editor.py -> ALL OK
Interaction harness: 36 checks, all pass — empty open, no-selection
  message, '..' + folder navigation, extension filter, picks persist
  (dirs at pick, selections at run), real match runs and auto-plays,
  simulated reboot restores selections, stale prefs degrade to unset,
  tournament multi-add (2 at once + 1 singly), row remove, and a real
  2-competitor tournament whose leaderboard contains exactly the
  chosen field.
Screenshots inspected: empty workspace, map browser, tournament
  setup list, post-run viewer.
```

## Known gaps carried forward

- Tournament maps remain "every shipped map" (2 curated maps) — maps
  weren't part of the request; add a map-selection list if the pool
  grows.
- Editor hazard authoring tool (MAP-08 🟡); SCO-03 decision.
