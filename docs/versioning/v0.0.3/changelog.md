# v0.0.3 Changelog

**Version:** 0.0.3
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

A pure UX round across the map editor and the playback viewer, raised
directly by the user from using the running app: no way back to the
menu from either screen, text-label tool buttons instead of icons, no
glanceable "what's active" indicator in the editor, and a harsh opaque
black grid on both canvases that read as graph paper instead of tissue.
No simulation logic, scoring, or JSON formats changed.

## Added

- `run.sh` — launcher script that creates `.venv` and installs
  `requirements.txt` on first run if missing, then execs
  `.venv/bin/python main.py "$@"`. Verified both the fresh-install and
  already-set-up paths.
- `nanobot/ui/icons.py` — a small vector-icon set drawn with
  `pygame.draw` primitives (no asset files, no new dependency), each
  cached per `(name, size, color)`: `pan_icon`, `edit_icon`,
  `delete_icon`, `habitas_icon`, `azn_icon`, `zone_icon` for the map
  editor; `play_icon`, `pause_icon`, `step_back_icon`,
  `step_forward_icon`, `speed_down_icon`, `speed_up_icon`,
  `back_arrow_icon` for the playback viewer. Every icon verified
  rendered and recognizable via direct screenshot inspection, not just
  present.
- Back-to-menu navigation in both screens, previously absent entirely:
  `MapEditorScreen.menu_btn` and `PlaybackViewer.btn_back`, each wired
  through an `on_back_to_menu` callback `App` assigns at construction,
  matching the existing `on_open_editor`/`on_open_playback` pattern. Both
  buttons show `icons.back_arrow_icon` alongside their text label rather
  than text alone, consistent with the rest of this version's icon work
  — `back_arrow_icon` was already drawn and cached in `icons.py` from
  earlier in this session but never actually wired into a button, since
  `Button` could only render an icon *or* text, never both; extended
  `Button.draw()` (`nanobot/ui/widgets.py`) to draw both side by side
  when a button has both, rather than leaving the icon unused or
  dropping the text (a bare arrow is ambiguous — back in history? close
  a panel? — without the word next to it).
- A top bar in the map editor (`MapEditorScreen._draw_top_bar`) showing
  the actual terrain texture, the actual stream texture + arrow (drawn
  via the renderer's own `_draw_stream_cell`, so it can't drift out of
  sync with what painting actually produces), or the active tool's icon
  — whichever the current tool implies — so the user can tell what will
  be placed on the next click without hunting through the sidebar for
  the one pressed button among eleven.

## Changed

- **Map editor sidebar** (`map_editor_sidebar.py`): Elements
  (Habitas/AZN/Zone) and Tools (Pan/Edit/Delete) sections converted from
  full-width text-label rows to 48×48 icon-button grids, with the old
  label moved into the existing tooltip mechanism. Header label
  y-positions now recorded once during `_build()` and replayed verbatim
  in `draw()`, instead of a parallel set of hand-computed offsets that
  could drift out of sync with the actual layout.
- **Playback viewer controls** (`playback_viewer.py`): play/pause, step
  back/forward, and speed down/up converted from text/symbol buttons
  ("Play", "<", ">", "-", "+") to icon buttons. `_toggle_play()` and the
  auto-pause-at-end branch in `update()` now swap `btn_play.icon` between
  `play_icon`/`pause_icon` instead of setting button text (the button no
  longer carries any). The "1.0x" speed label is now positioned relative
  to the actual `btn_speed_down`/`btn_speed_up` rects rather than a
  hardcoded coordinate, so it can't end up misaligned the next time a
  button either side of it moves.
- **Grid lines, both canvases** (`map_canvas_renderer.py`,
  `playback_viewer.py`): `GRID_COLOR` changed from opaque black
  `(0, 0, 0)` to a translucent warm-dark `(25, 12, 12, 70)`, drawn onto a
  dedicated `pygame.Surface(..., pygame.SRCALPHA)` overlay and blitted
  once per frame rather than via `pygame.draw.rect()` directly on the
  main surface per cell (see Fixed, below, for why that distinction
  matters). One shared overlay per draw call, not one per cell, avoids
  thousands of tiny surface allocations on a large map.
- **`main.py` ESCAPE handling**: now checks
  `getattr(self.current, "modal", None) is not None` before falling back
  to "go to menu" — if a modal is open (e.g. the editor's save/load
  dialog), the event is routed through the screen's own
  `handle_event()` so its modal-cancel logic runs first, instead of
  unconditionally jumping past the modal straight to the menu.

## Fixed

**pygame's `draw.rect()` ignores alpha on a non-alpha surface.** The
original fix attempt — just giving `GRID_COLOR` an alpha component and
drawing it the same way as before — silently did nothing; the grid
stayed fully opaque regardless of the alpha value. Confirmed directly by
drawing a translucent rect and reading the resulting pixel back with
`surface.get_at()`: the blended color was unaffected by alpha entirely.
Root cause: `pygame.draw.rect()` draws fully opaque onto any surface
that doesn't itself carry per-pixel alpha, which the main display
surface doesn't. Fixed by routing grid lines through a dedicated
`SRCALPHA` overlay surface instead, in both `map_canvas_renderer.py` and
`playback_viewer.py`.

**Sidebar resize staleness (`map_editor_sidebar.py`).** Confirmed by
resizing the window and observing every sidebar button stay frozen at
its build-time position while the panel background (read from
`self.rect` directly) moved with the new width — clicks on a button
after a resize would land on the wrong row. A full `_build()` rebuild
was rejected as the fix since it would reset whichever density/stream/
tool button is currently pressed back to hardcoded defaults, discarding
the user's actual selection. Fixed instead by shifting every button's
`rect.x` by the same delta the panel itself moved, in `resize()`.

**Menu button invisible, hidden under the sidebar (`map_editor.py`).**
The new Menu button was originally drawn inside `_draw_top_bar()`, which
ran *before* `self.sidebar.draw(surface)` — the sidebar's opaque
background silently painted over it every frame. Confirmed via
screenshot (the button was present and correctly handled clicks, just
never visible). Fixed by moving the draw call to after the sidebar in
`MapEditorScreen.draw()`.

**`_draw_stream_cell` called with the wrong argument shape.** Caught
before it ever ran: the top bar's stream preview initially called it
with separate x/y/size positional arguments, but the real signature
takes a single `pygame.Rect`. Fixed by checking the actual signature via
grep before wiring up the call.

**Resizing the playback viewer mid-playback silently flipped the
play/pause icon back to "play."** `resize()` calls `_build_controls()`
to rebuild every control at its new screen-relative position, which
also rebuilds `btn_play` from scratch with its hardcoded default `play`
icon — regardless of whether playback was actually still running.
Confirmed directly: start playback, resize the window, observe
`self.playing` is still `True` but the button now shows the play
triangle instead of the pause bars, with no actual change to whether
the simulation is advancing. Fixed by restoring the icon that matches
`self.playing` immediately after `_build_controls()` runs inside
`resize()`. Same root cause as the sidebar resize-staleness bug above —
a rebuild silently discarding state a delta-shift would have preserved
— caught here because rebuilding was the simpler implementation for a
viewer with no per-button toggle state to preserve otherwise, and the
one button that *does* carry state (play vs. pause) was the one missed.

## Verification

```
$ pytest tests/
280 passed in 0.76s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy0 strategies/example_strategy.py \
    --strategy1 strategies/example_strategy_v2.py --seed 42
HeadlessRunner: match complete in 1500 turns
HeadlessRunner: winner — player 0
```

Plus direct visual verification for everything not coverable by the
above: every new icon rendered and inspected at actual size
(`/tmp/icon_check.png`, `/tmp/playback_icon_check.png`); the map editor's
top bar, icon+text Menu button, icon sidebar, and softened grid rendered
and inspected (`/tmp/editor_menu_check.png`); the playback viewer's icon
controls, icon+text Back to Menu button, play/pause icon swap,
repositioned speed label, and softened grid all rendered and inspected
(`/tmp/playback_check.png` showing the paused state,
`/tmp/playback_check_playing.png` confirming the icon swaps to pause
while playing). The resize-while-playing fix verified by directly
toggling play, calling `resize()`, and checking `btn_play.icon` matches
`play_icon`/`pause_icon` by object identity, not just by eye. No
`nanobot/core/` or `nanobot/tournament/` file was touched this version —
confirmed the headless match run above produces a normal result, not
just that it doesn't crash.

## Known gaps carried forward

- No unit tests for the pygame rendering/input layers themselves — same
  gap v0.0.2's plan.md named and left open; this version's verification
  continues to rely on screenshot/integration checks rather than a unit
  suite for `icons.py`, `map_canvas_renderer.py`, or `playback_viewer.py`.
- No CI wiring.
