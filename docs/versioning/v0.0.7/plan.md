# v0.0.7 — Run Match Workspace, Panning, Sprite Visibility Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Extend the playback viewer into the actual "Run Match" workspace rather
than adding a third screen — reuse the exact picker pattern already
built and proven in v0.0.5, factored into a shared widget so it's
written once. Fix panning by adding a second, more universally-usable
input method instead of replacing the existing one. Fix sprite
visibility by adjusting render size (default zoom, icon inset), not by
changing what's drawn.

## Order

1. **Extract `FilePickerModal`** (`widgets.py`) from the main menu's
   existing bespoke modal code — needed a second time, so worth not
   copy-pasting the same ~50 lines into a second file.
2. **Refactor `MainMenu`** to use it, verify via the existing test suite
   plus a direct picker-interaction test that nothing regressed.
3. **Two-row top bar in `PlaybackViewer`**: row 1 (existing playback
   controls + Back to Menu) unchanged; row 2 (new) holds Map/P1/P2
   selector buttons and a Restart button. `CONTROL_BAR_HEIGHT` becomes
   the sum of both row heights — every other layout calculation already
   references it symbolically, so this cascades without needing to touch
   each one by hand.
4. **Selection state + restart threading in `PlaybackViewer`**: seeded
   from whatever produced the currently-loaded replay
   (`log.player_strategies`, the map resolved from `log.map_name`),
   falling back to glob defaults if either is unresolvable. Restart
   reuses the exact background-thread pattern `main_menu.py` already
   established (and the exact reason: a multi-second simulation must not
   block the redraw loop). On completion, swap in the new log/map via a
   factored-out `_load_replay()` (also used by `__init__`) rather than
   duplicating the loading logic.
5. **Pan fix**: add left-button drag-to-pan, disambiguated from
   click-to-select-a-bot by whether any `MOUSEMOTION` happened between
   button-down and button-up. Keep the existing middle-drag as a second,
   optional method — not a replacement.
6. **Sprite visibility fix**: raise default zoom (1.0 → 1.5) and zoom
   ceiling (3.0 → 6.0), shrink the bot icon's team-ring inset
   (`r.width // 6` → `r.width // 10`) so more of the cell is the actual
   sprite.
7. Fix the Escape-key bug found while testing (analysis.md §6):
   `main.py` now checks both `self.modal` (map editor) and
   `self.picker.is_open` (main menu, playback viewer) before deciding
   whether to let the current screen handle Escape itself.
8. Verify every piece by direct interaction (not just code review):
   render-and-crop the bot sprite at old vs. new size; synthetic
   mouse-down/motion/mouse-up sequences for both drag-to-pan and
   true-click-to-select; a full picker-select → restart → wait-for-
   completion → check-new-log-loaded cycle; the Escape-vs-picker fix
   tested as the literal key sequence a user would trigger.
9. Full regression sweep (pytest, `tests/check_editor.py`, a real
   headless CLI match with the correct flags).

## Explicit non-goals for this version

- No change to the map editor's own pan tool — already left-drag-based
  and already working; this version's pan fix is specific to the
  playback viewer, which had no tool-selector concept to begin with.
- No persistence of zoom/scroll position across a Restart — resets to
  the same default every time, matching how a brand-new `PlaybackViewer`
  already behaves; not asked for, and would add state-tracking
  complexity for a minor convenience.
- No change to the main menu's own "Run Match" flow beyond the
  `FilePickerModal` extraction — it still creates a fresh
  `PlaybackViewer` per match; the new in-viewer Restart is what lets you
  avoid going back to the menu for a second match, not a replacement for
  the menu's own first-match entry point.
