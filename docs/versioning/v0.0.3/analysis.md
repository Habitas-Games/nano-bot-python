# v0.0.3 — UX Follow-up Analysis

**Status:** Complete
**Depends on:** [../v0.0.2/changelog.md](../v0.0.2/changelog.md) (correctness/robustness QA, now closed out at 280 tests)

---

## 1. Scope of this version

Every prior version (v0.0.1's UX pass, v0.0.2's nine QA rounds) focused on
*correctness*: does the simulation produce the right numbers, does the
editor save the right JSON, does a bad input fail cleanly instead of
crashing. None of that touches whether the app is pleasant or even fully
usable to operate by hand. This version is a pure UX round, raised
directly by the user after using the running app rather than found by
reading code:

1. "there is no way to return from the map or the simulator to the menu."
2. "as UX I want icons rather than text like pan, edit etc."
3. "I want to see the tile to draw and have the active tile or tool on a
   tile at the top so I know what is active on the map editor."
4. "there is a grid on the editor [that] does not look like a part of the
   body, the black border is not likable."
5. "also the ux of the simulator please review it" — explicitly extending
   the same review to the playback viewer, not just the editor.

No simulation logic, JSON formats, or scoring changed in this version.

## 2. Finding: no way back to the menu

Confirmed by tracing the actual event loop in `main.py`: once
`App._open_editor()` or `App._open_playback()` switched `self.current`
away from the menu, nothing pointed back. Neither `MapEditorScreen` nor
`PlaybackViewer` had a "Menu" control, and the global `ESCAPE` handling
that existed jumped straight to the menu unconditionally — which is
**worse** than no handling at all once a screen has its own modal open
(e.g. the editor's save/load file-name dialog), since it would blow past
the modal's own cancel behavior and abandon the screen entirely.

**Fix:** an explicit on-screen "Menu" control in both screens
(`MapEditorScreen.menu_btn`, `PlaybackViewer.btn_back`), wired through a
`on_back_to_menu` callback each screen exposes and `App` assigns at
construction time — the same pattern already used for
`on_open_editor`/`on_open_playback`/`on_open_tournament`. The global
`ESCAPE` handler in `main.py` now checks
`getattr(self.current, "modal", None) is not None` first and defers to
the screen's own `handle_event()` when a modal is open, falling back to
"go to menu" only when there isn't one.

## 3. Finding: text-label tool buttons don't read at a glance

The map editor sidebar's Elements (Habitas/AZN/Zone) and Tools
(Pan/Edit/Delete) sections were full-width rows of text labels — six rows
stacked vertically, each requiring the user to actually read the word to
know what it does. A toolbar is supposed to be scannable by shape, not
read like a sentence.

**Fix:** built a small vector-icon set (`nanobot/ui/icons.py`) — drawn
with `pygame.draw` primitives directly (no asset files needed, no new
dependency), cached per `(name, size, color)` so repeated calls are free.
Converted both sections to a 3-column grid of 48×48 icon buttons with the
old label moved into the existing tooltip mechanism. Verified each icon
is actually recognizable, not just present, by rendering them to a PNG
and inspecting it directly (`/tmp/icon_check.png`,
`/tmp/playback_icon_check.png`) rather than trusting the drawing code by
inspection alone.

## 4. Finding: no glanceable "what's currently active" indicator

Before this round, the only way to know which tool or terrain/stream
value was selected was to find the one pressed-looking button among
eleven in the sidebar. For terrain and stream specifically, "pressed"
also didn't show *which* texture or arrow direction was selected — just
that some button in that row was down.

**Fix:** a top bar in the map editor showing the actual thing that will
be placed on the next click — the real terrain texture, the real stream
texture plus arrow (drawn via the renderer's own
`_draw_stream_cell`, not a re-implementation, so it can never drift out
of sync with what painting actually produces), or the relevant tool's
icon otherwise — followed by the existing status text. This needed
`STATUS_BAR_HEIGHT` to grow from 26 to 44 to fit a 32×32 preview
comfortably.

## 5. Finding: the grid reads as graph paper, not tissue

`GRID_COLOR` was flat opaque black (`(0, 0, 0)`), drawn with
`pygame.draw.rect(..., width=1)` directly onto the canvas per cell. At
the zoom levels the editor actually uses this produces a dense black
lattice that dominates the terrain colors underneath rather than
reading as cell boundaries within living tissue.

**The straightforward fix — give `GRID_COLOR` an alpha component — does
not work**, and confirming *why* mattered: `pygame.draw.rect()` ignores
the alpha channel and paints fully opaque on any surface that doesn't
itself have per-pixel alpha, which the main display surface doesn't.
Confirmed directly by drawing a translucent rect and reading the
resulting pixel back with `surface.get_at()` — the alpha component had
no effect at all on the blended color, opaque black went in, opaque
black came out.

**Fix:** route grid lines through a dedicated `pygame.Surface(...,
pygame.SRCALPHA)` overlay — one per draw call, not one per cell, to
avoid thousands of tiny surface allocations on a large map — drawn onto
with the same `GRID_COLOR`, then blitted once onto the main surface
after all cells are drawn. `GRID_COLOR` changed to `(25, 12, 12, 70)`, a
warm, mostly-transparent dark tone that still marks boundaries precisely
enough for editing without fighting the red/green/purple tissue palette.
Applied identically in `map_canvas_renderer.py` (the editor) and
`playback_viewer.py` (the simulator), since both had the exact same
`(0, 0, 0)`-opaque grid drawn the exact same way.

## 6. Extending the review to the playback viewer

The user's request was general ("review it"), not limited to the two
specific issues already raised for the editor. Generated a fresh replay
and rendered the actual running viewer to inspect it directly rather
than assuming the editor's issues were the only ones present. Found the
same two issues, present for the same underlying reason (both screens
were built early in the port and never revisited for UX):

- The same opaque-black grid (§5), fixed the same way.
- Play/Pause/step/speed controls were plain text/symbol buttons ("Play",
  "<", ">", "-", "+") rather than icons — same shape of issue as §3,
  fixed the same way with seven additional icons
  (`play_icon`/`pause_icon`/`step_back_icon`/`step_forward_icon`/
  `speed_down_icon`/`speed_up_icon`/`back_arrow_icon`).

The HUD (scores, turn counter, bot-alive counts) and inspector panel were
checked and found legible and correctly laid out already — no changes
needed there.

## 7. Incidental findings, fixed in passing

Two real bugs surfaced while making the above changes, neither raised by
the user directly but both confirmed by execution before being treated
as real:

- **Sidebar resize staleness.** `MapEditorSidebar.resize()` updated
  `self.rect.x` to track the new screen width but left every button's
  rect frozen at its build-time position — confirmed by resizing the
  window and observing buttons stay put while the panel background (read
  from `self.rect` directly) moved out from under them. A full rebuild
  was rejected as the fix because it would reset whichever
  density/stream/tool button is currently pressed back to hardcoded
  defaults, discarding the user's actual selection; fixed instead by
  shifting every button's `rect.x` by the same delta the panel moved.
- **Menu button hidden under the sidebar.** The new "Menu" button was
  initially drawn inside `_draw_top_bar()`, which runs *before*
  `self.sidebar.draw(surface)` — the sidebar's opaque background painted
  over it, so it existed and correctly handled clicks but was invisible.
  Confirmed via screenshot, fixed by moving the draw call to after the
  sidebar in `MapEditorScreen.draw()`.

## 8. Process note

Continued the discipline established in v0.0.2: every claim here is
backed by actually running the code and looking at the result — pixel
inspection for the alpha-blending finding, rendered PNGs for every icon
and layout change, a real resize for the sidebar staleness bug, a real
screenshot for the hidden-button bug — not by reading the drawing code
and concluding it looks right.
