# v0.0.5 — Match Setup & HUD Parity Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Reuse existing patterns rather than introduce new ones: the main menu's
picker reuses the map editor's `self.modal = {"type": ..., ...}`
dict-driven modal pattern (`map_editor.py`'s `load_picker`) instead of a
new dropdown widget, and the HUD's new sections are positioned via a
once-computed layout dict (`_compute_hud_layout`) rather than hand-typed
offsets — the same anti-drift fix already applied to the map editor
sidebar's headers.

## Order

1. **`Slider` widget** (`widgets.py`) — click-or-drag-anywhere-on-track
   scrubber, generic enough to reuse if another jump-to-value control is
   ever needed elsewhere.
2. **Playback viewer HUD**: `_compute_hud_layout()` computes every
   section's y-position once (map info, turn, slider, scores, winner,
   legend) since the row counts are known as soon as the log loads;
   `_draw_hud` reads from it instead of hand-computing. `_jump_to()`
   mirrors `playback_scene.gd`'s `jump_to` exactly: relocate + reset the
   frame-accumulator, leave `self.playing` untouched. `_draw_inspector`
   loses its `if selected_bot_id is None: return` early-out in favor of
   an always-drawn panel with a placeholder line.
3. **Main menu selection UI**: three selector buttons opening the modal
   picker, default selection computed once at startup (first map, first
   two distinct strategies — preserves the old implicit behavior for a
   user who never touches the pickers), `_run_match` re-checks the
   selected paths still exist before launching (a file could be deleted
   after being selected, or never have existed if the folders were
   empty at startup).
4. Verify each piece by direct interaction, not just by reading the
   code: simulate a slider drag and check `current_frame` actually
   changed by the predicted amount; simulate opening the map-picker modal
   and clicking a row and check `selected_map` and the button's label
   both updated; run a real match end-to-end through `MainMenu._run_match
   ()` → `update()` polling loop and check the resulting summary
   message names the actually-selected strategy files.
5. Full regression sweep (pytest, `tests/check_editor.py`, a real
   headless CLI match).

## Explicit non-goals for this version

- No uniqueness constraint between Player 1 and Player 2 strategy
  selection — Godot's two dropdowns don't enforce this either (self-play
  is allowed), so neither does this.
- No persistence of the user's selection across app restarts — Godot
  doesn't persist it either; it resets to the first scanned map/
  strategies every time `main_menu.gd`'s `_ready()` runs.
- No tournament-screen changes — the tournament screen already runs
  every strategy file found, by design; it has no equivalent "which two"
  selection to add.
