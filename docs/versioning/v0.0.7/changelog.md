# v0.0.7 Changelog

**Version:** 0.0.7
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Turns the playback viewer into the actual "Run Match" workspace: map and
strategy selection (previously only on the main menu) now live on this
screen too, with a Restart button that re-simulates in place. Fixes
panning, which only worked via an awkward middle-mouse-drag many input
devices can't do comfortably — left-drag now works too. Fixes bot
sprites rendering too small to be recognizable at the default zoom.
Also fixes an Escape-key bug the new picker exposed in `main.py`.

## Added

- **`nanobot/ui/widgets.py`**: `FilePickerModal` — extracted from the
  main menu's bespoke modal code (now used in two places, not worth
  copy-pasting a third time).
- **`nanobot/ui/playback/playback_viewer.py`**: a second top-bar row
  with "Map: ...", "P1: ...", "P2: ..." picker buttons and a "▶ Restart"
  button. Picking a file updates the button label immediately; Restart
  re-simulates with the current selection on a background thread
  (`_match_worker`, the same pattern `main_menu.py` already uses for the
  same reason) and swaps the loaded replay in place when done, resetting
  to turn 1 and updating the turn slider's range. A spinner + "Simulating...
  Ns" indicator shows while it's running; all controls are disabled
  during that window the same way the main menu already disables its own
  buttons during a match.
- Left-button drag-to-pan, alongside the existing middle-drag (kept,
  not replaced) — disambiguated from a click-to-select-a-bot by whether
  any mouse motion happened between button-down and button-up.

## Changed

- **`nanobot/ui/main_menu.py`** refactored to use the new
  `FilePickerModal` instead of its own bespoke modal dict/draw/handle
  code — same behavior, less duplicated logic now that a second screen
  needs the identical thing.
- **Default zoom** 1.0 → 1.5, **max zoom** 3.0 → 6.0, and the bot
  sprite's team-ring inset shrunk (`r.width // 6` → `r.width // 10`) —
  at the old defaults a 16px bot sprite rendered at roughly 10×10
  pixels, indistinguishable from a generic blob; confirmed by rendering
  and cropping a bot close-up before and after.
- `CONTROL_BAR_HEIGHT` is now the sum of two row heights (`TOP_ROW_HEIGHT
  = 50`, `SETUP_ROW_HEIGHT = 40`) instead of a single flat value — every
  other layout calculation in the file already referenced the constant
  symbolically, so this cascaded correctly without touching each one.

## Fixed

**Panning required a middle-mouse-button drag, which many trackpads and
mice have no comfortable way to perform.** Confirmed the existing logic
itself was correct (a synthetic event with `buttons=(0,1,0)` panned
correctly) — the gap was input-method availability, not broken code.
Added left-drag as a second method: track the mouse-down position and
whether any motion occurred before release; a true click (no motion)
selects the nearest bot as before, any drag pans instead.

**Bot sprites were technically real but visually unrecognizable at the
default zoom.** See analysis.md §4 for the close-up crop comparison.
Not a code bug — the real sprite was always being blitted — but a real
UX problem: at the size it actually rendered, it read as "not using the
sprites" because no detail survived the downscale.

**`main.py`'s Escape handling didn't recognize the new
`FilePickerModal`.** It only checked for a bare `self.modal` attribute
(the map editor's dialog shape) — `PlaybackViewer` and the refactored
`MainMenu` now hold their modal state in `self.picker` instead, so
Escape while a picker was open fell through to "go to menu" rather than
closing the picker, discarding whatever the user was doing on that
screen. Confirmed by testing the literal sequence (open picker, press
Escape, check the picker closed *and* the screen didn't change) before
and after the fix. Now checks both shapes via `getattr`/duck-typing.

## Verification

```
$ pytest tests/
280 passed in 0.76s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy_a strategies/example_strategy.py \
    --strategy_b strategies/example_strategy_v2.py --seed 7
HeadlessRunner: match complete in 1500 turns
HeadlessRunner: winner — player 1
  player 1: 160 pts
```

Plus direct interaction tests for everything code review alone
couldn't confirm:
- Rendered a bot close-up at the old zoom/inset (10×10px, unrecognizable
  blob) and the new zoom/inset (clearly legible ring-and-dot design) —
  both saved as crops and visually compared.
- Synthetic mouse-down → motion → mouse-up sequence confirmed left-drag
  pans (`scroll_x`/`scroll_y` changed) and leaves `selected_bot_id`
  untouched; a separate down-up-with-no-motion sequence at a bot's exact
  position confirmed it still selects that bot.
- Full picker → restart → poll-until-complete cycle: picked a different
  Player 2 strategy via the picker, clicked Restart, polled `update()`
  until the background thread finished, and confirmed the viewer's
  `log`/`current_frame`/`turn_slider` range all reflect the new match,
  not the old one.
- The Escape-vs-picker fix tested as the literal key sequence: opened
  the map picker, dispatched a real `K_ESCAPE` `KEYDOWN` through the same
  branch `main.py`'s event loop uses, confirmed the picker closed *and*
  `app.current` was still the playback viewer (not bounced to the menu).
- Full app flow end-to-end: `MainMenu._run_match()` → background thread
  → `on_open_playback` → `PlaybackViewer` opens showing the just-run
  match, screenshotted and visually inspected.

## Known gaps carried forward

- No unit tests for the pygame rendering/widget layer — same gap named
  in every prior version.
- `assets/menu/` and `assets/fx/` remain unported (raised in an earlier
  conversation, separate scope).
- Zoom/scroll position isn't preserved across a Restart (plan.md's
  explicit non-goal).
