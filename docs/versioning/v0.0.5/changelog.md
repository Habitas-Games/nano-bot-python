# v0.0.5 Changelog

**Version:** 0.0.5
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Two gaps raised together: the main menu's "Run Match" had no way to
choose which map or strategies to use (it silently used the
alphabetically-first map and first two strategy files every time), and
the playback viewer's HUD was missing several sections the Godot
original always had (map name, a map legend, a turn-jump slider, an
always-visible bot inspector). Also confirms: strategy files are, and
have always been, plain Python — no Godot/GDScript or Godot install
involved anywhere in this project.

## Added

- **`nanobot/ui/widgets.py`**: `Slider` — a horizontal scrubber, click or
  drag anywhere on the track to jump straight to a value (not just
  step), used for the playback viewer's turn-jump control.
- **`nanobot/ui/main_menu.py`**: three selector buttons ("Map: ...",
  "Player 1 Strategy: ...", "Player 2 Strategy: ...") above "Run Match,"
  each opening a modal file-picker (reusing the map editor's existing
  modal pattern) listing every `*.json` map / `*.py` strategy found.
  Default selection on startup matches the old implicit behavior (first
  map, first two distinct strategies) so a user who never touches the
  pickers sees no change in behavior.
- **`nanobot/ui/playback/playback_viewer.py`**:
  - A "Map: {name}" header above the turn counter.
  - A turn-jump slider directly below the turn counter, wired to a new
    `_jump_to()` that relocates `current_frame` and resets the frame
    accumulator without touching `self.playing` — matches
    `playback_scene.gd`'s `jump_to` exactly (scrubbing while playing
    keeps playing from the new position; scrubbing while paused stays
    paused).
  - A "Map Legend" section: the same seven icon+label rows as
    `hud.gd`'s `legend_entries` (4 densities, bloodstream, habitas
    point, AZN node), reusing the textures already loaded for the
    canvas rather than loading separate copies.
  - `_compute_hud_layout()`: every HUD section's y-position computed
    once (depends only on player count, known as soon as the log
    loads) instead of hand-computed inline in `_draw_hud` — same
    anti-drift fix as the map editor sidebar's header positions.

## Changed

- **`_draw_inspector`** no longer returns early when nothing is
  selected — it now always draws the panel with a "Bot Inspector"
  header, showing "Click a bot on the map to inspect it." as a
  placeholder. Matches `hud.gd`'s persistent inspector panel, and means
  a first-time user can see right away that bots are clickable instead
  of only discovering the panel exists after clicking one by accident.
  Panel height increased (130px → 150px) to fit the new header line
  without crowding the 7 detail lines.
- **`MainMenu._run_match()`** now uses `self.selected_map`/
  `self.selected_p0`/`self.selected_p1` (settable via the new pickers)
  instead of unconditionally grabbing `sorted(glob(...))`'s first
  results. Still validates all three resolve to existing files before
  launching, with an updated message naming what's missing.

## Confirmed, not changed

**Strategy files are plain Python, with no Godot dependency at all.**
`STRATEGIES_DIR`'s glob has only ever matched `*.py`
(`nanobot/ui/main_menu.py`, unchanged this version), and both bundled
examples (`strategies/example_strategy.py`, `example_strategy_v2.py`)
are ordinary Python classes implementing
`nanobot.api.nano_strategy.NanoStrategy` — no `.gd` files, no Godot
editor or compiler involved anywhere in writing, loading, or running a
strategy in this project.

## Verification

```
$ pytest tests/
280 passed in 0.79s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy0 strategies/example_strategy.py \
    --strategy1 strategies/example_strategy_v2.py --seed 42
HeadlessRunner: match complete in 1500 turns
HeadlessRunner: winner — player 0
```

Plus direct interaction tests, not just code review: simulated a real
mouse click at the turn slider's exact midpoint and confirmed
`current_frame` jumped to 750/1499 as predicted; simulated clicking a
bot's exact screen position and confirmed the now-always-visible
inspector showed its real live data; opened the main menu's map-picker
modal, clicked the first file row, and confirmed both `selected_map`
and the button's displayed label updated; ran a complete match through
`MainMenu._run_match()` → polling `update()` until the background thread
finished, and confirmed the resulting summary message correctly named
the actually-selected strategy files (not the old hardcoded
alphabetically-first ones). Screenshots taken of the main menu, its
open picker modal, and the playback viewer's new HUD sections, all
visually inspected before considering this done.

## Known gaps carried forward

- No unit tests for the pygame rendering/widget layer — same gap named
  in every prior version's changelog.
- The main menu's background/logo and the playback viewer's event VFX
  (`assets/menu/`, `assets/fx/`) remain unported, as already noted in
  v0.0.4.
