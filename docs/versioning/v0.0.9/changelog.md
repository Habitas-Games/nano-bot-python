# v0.0.9 Changelog

**Version:** 0.0.9
**Status:** Complete
**Depends on:** [../v0.0.7/changelog.md](../v0.0.7/changelog.md) (added the picker UI this version removes from the wrong screen)

---

## Summary

Corrects a misread instruction from v0.0.7. The user's original request —
"selecting the world, and strategies should be on the run match window"
— meant the map/strategy pickers should live *only* on the match/playback
screen, replacing where they'd been since v0.0.5 (the main menu). v0.0.7
added them to the playback viewer but left the original main-menu copies
in place too, so both screens ended up with picker UI instead of just
the one that was actually asked for.

## Changed

- **`nanobot/ui/main_menu.py`**: removed the "Map: ...", "P1: ...",
  "P2: ..." picker buttons, the `FilePickerModal` instance, and the
  `selected_map`/`selected_p0`/`selected_p1` state that backed them —
  all of it, along with the modal draw/handle wiring. `_build_buttons()`
  is back to its pre-v0.0.5 four-button layout (Run Match, Map Editor,
  Tournament, Quit), vertically centered the same way. `_run_match()`
  goes back to globbing the first map and first two strategies fresh
  each call, since there's no longer any UI on this screen to ever
  change that — picking what to run now happens entirely on the
  playback viewer (v0.0.7's "Map:"/"P1:"/"P2:" buttons + Restart),
  which is unchanged by this version.

## Verification

```
$ pytest tests/
296 passed in 1.10s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy_a strategies/example_strategy.py \
    --strategy_b strategies/example_strategy_v2.py --seed 1
HeadlessRunner: match complete in 1500 turns
HeadlessRunner: winner — player 1
```

Plus a full app-flow check: `MainMenu._run_match()` (now picker-free) →
background thread → `on_open_playback` → `PlaybackViewer` opens showing
the match, with its own Map/P1/P2/Restart row intact and functional —
screenshotted and visually confirmed both screens now match what was
actually asked for.
