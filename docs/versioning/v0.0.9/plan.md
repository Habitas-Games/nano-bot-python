# v0.0.9 — Picker Placement Correction Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Remove, not refactor: delete the main menu's picker buttons, modal
instance, and backing selection state entirely rather than disabling or
hiding them, since none of it has any remaining purpose once the
playback viewer is the only place selection happens. Restore
`_run_match()` to its pre-v0.0.5 shape (fresh glob each call) instead of
leaving now-pointless cached-selection plumbing in place with no UI left
to drive it.

## Order

1. Remove `btn_select_map`/`btn_select_p0`/`btn_select_p1` and the
   `FilePickerModal` import/instance from `MainMenu`.
2. Remove `_open_map_picker`/`_open_strategy_picker`/
   `_apply_picker_choice`/`_refresh_selector_labels` and the
   `selected_map`/`selected_p0`/`selected_p1`/`_init_default_selection`
   state they backed.
3. Restore `_build_buttons()`'s simple four-button vertical layout and
   `_run_match()`'s fresh-glob-each-call behavior.
4. Verify: full test suite, the editor integration script, a real
   headless match, and a full app-flow check confirming `MainMenu` now
   renders picker-free while `PlaybackViewer` still has its own pickers
   and Restart button fully intact and functional.

## Explicit non-goals for this version

- No changes to `PlaybackViewer` — its picker/Restart UI is exactly what
  was asked for in v0.0.7 and stays as-is.
- No changes to `FilePickerModal` itself (`widgets.py`) — still used by
  `PlaybackViewer`, just no longer by `MainMenu`.
