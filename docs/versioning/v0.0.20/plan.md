# v0.0.20 — Review Findings Fix-All Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Engine truth first (failure events exist before anything can display
them), then shared widgets, then each screen, then one harness that
re-probes every original finding. Every fix re-verified by the same
probe that demonstrated the defect.

## Order

1. **Engine**: `_call_strategies` gains the events list; emits
   `strategy_error` (exception type + message, truncated) and
   `strategy_timeout` (measured ms). +3 tests; one existing test's
   call-site signature updated.
2. **Viewer**: `_event_text` for both event kinds (warning-colored in
   the ticker); timeline collapses consecutive identical lines;
   missing-map detection in `_load_replay` + red canvas banner +
   "(file missing!)" HUD marker; ticker rows clickable
   (`_jump_to_turn` maps turn→frame index; rects reset before the
   fits-check early-return so stale rects can't ghost-click); C
   follow camera (centers each frame, released by pan/F); replay
   picker lists all files with delete callback.
3. **Widgets**: FilePickerModal — wheel scroll, visible-rows window,
   shared `_draw_scrollbar`, optional `on_delete` with per-row [x]
   that keeps the modal open; FileBrowserModal — type-to-filter
   (substring, Esc clears first), filter indicator, scrollbar reuse.
4. **Editor**: MapHistory redo stack (undo snapshots the post-edit
   state at undo time; save_state clears the branch; position moves
   in lockstep for dirty tracking) + Ctrl+Y/Ctrl+Shift+Z + sidebar
   Undo|Redo split row + per-frame enable sync; top-bar status text
   truncates to the space before the filename label. +4 history
   tests.
5. **Tournament**: competitor window (8 rows + wheel + range line);
   "Maps…" multi-select with `_maps_in_play()` fallback to all;
   button label reflects the subset; setup screen lists map names.
6. **Menu**: Guide button (webbrowser, file:// URL, failure-tolerant);
   5-row stack re-clamped.
7. **Paths**: normpath every UI module's dir constants (prefs and
   equality-check hygiene — found when the harness's path comparison
   failed against a `../..`-laden picker entry).
8. **Verification**: 352 tests; check_editor; 31-check harness;
   screenshot inspection.
9. **Docs**: STR-05 / VIS-04 / UX-01 / TRN-01 / MAP-08 rows; guide
   (iterate step, time-budget visibility, redo); v0.0.20 folder;
   commit + push.

## Explicit non-goals

- SCO-03 — scoring-rule decision reserved for the user; the only M7
  item left open.
- Editing committed patrol waypoints / per-patrol stats UI — standing
  v0.0.19 non-goals.
