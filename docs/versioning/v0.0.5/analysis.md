# v0.0.5 — Match Setup & HUD Parity Analysis

**Status:** Complete
**Depends on:** [../v0.0.4/changelog.md](../v0.0.4/changelog.md)

---

## 1. Trigger

Two related complaints raised together: "the match needs a way to select
the map and also the strategies competing before start," and "there were
plenty of stats shown in the original but now not working." A third
remark — "the new strategy codes should be in python" / "no need of
godot compiler, so python" — needed confirming rather than building,
since it was already true.

## 2. Match setup: what Godot has that Python never did

Reading `main_menu.gd` (`_build_ui`, `_scan_maps_and_strategies`,
`_on_run_match`) showed it has always had three `OptionButton` dropdowns
— map, Player 1 strategy, Player 2 strategy — populated by scanning
`res://maps/*.json` and `res://strategies/*.gd`, with the user's actual
selection read at `_on_run_match` time.

The Python `MainMenu._run_match()` never had an equivalent. It called
`sorted(glob.glob(...))` for both maps and strategies and unconditionally
used `maps[0]` and `strategies[:2]` — alphabetically-first, with no UI
exposing that choice or any way to override it. This was never a
regression introduced by a later change; it's how `_run_match` was
written from the very first Python port and never revisited.

## 3. Stats: what Godot's HUD shows that Python's didn't

`hud.gd`'s `_build_ui` lays out, top to bottom: a map name + turn-count
header, the turn counter, per-player score rows, a **Bot Inspector**
panel that's always present (showing a "Click a bot..." placeholder when
nothing's selected, not only appearing once something is), a **Map
Legend** (icon + label for every density, the bloodstream, the habitas
marker, the AZN node), and a **turn slider** ("Jump to turn") that can
relocate playback to any frame directly, not just step by one.

`playback_viewer.py`'s `_draw_hud`/`_draw_inspector` before this version
had only the turn counter and score rows — the map name, the legend, the
slider, and the always-visible inspector were all missing. This wasn't
a separate visual bug like the asset-texture gap from v0.0.4; it's
content that was simply never built, most likely because it's
non-trivial UI work (a custom slider widget, a fixed layout budget for
the new sections) rather than a one-line asset swap. The user's "not
working" most likely refers to this content being entirely absent rather
than present-but-broken — confirmed by reading the pre-v0.0.5
`_draw_hud` directly: there is no legend code, no slider code, and the
inspector is gated behind `if self.selected_bot_id is None: return`.

## 4. Strategy language

`MainMenu`'s `STRATEGIES_DIR` glob has always matched `*.py` only — the
example strategies (`strategies/example_strategy.py`,
`example_strategy_v2.py`) are plain Python implementing
`nanobot.api.nano_strategy.NanoStrategy`, no Godot/GDScript involved at
any point in the Python project, and no Godot installation or compiler
is needed to write or run one. This needed only confirming to the user,
not building — see the changelog for the exact statement given back.

## 5. Scope boundary

This version touches `nanobot/ui/main_menu.py` (selection UI),
`nanobot/ui/widgets.py` (new `Slider` widget), and
`nanobot/ui/playback/playback_viewer.py` (HUD content). No simulation
logic, scoring, or JSON formats changed — `_run_match`'s validation and
`_match_worker`'s signature are unchanged except for which paths get
passed in.
