# v0.0.1 — Port Analysis

**Status:** Complete (written alongside the port, not strictly before it — see plan.md note)
**Reference:** [../../requirements.md](../../requirements.md), the Godot project's `src/core/*.gd`, `src/api/*.gd`, `src/runner/*.gd`, `src/tournament/*.gd`, and `docs/versioning/v0.0.3/` (the map editor cleanup whose lessons this port applies from the start).

---

## 1. Why this project exists

The Godot/GDScript implementation (`nano-bot`) accumulated friction that
wasn't really about game-engine features: GDScript's global `class_name`
resolution depends on an editor-built cache that doesn't exist in a fresh
headless run (had to be rebuilt explicitly during the v0.0.3 verification
work), duplicate function definitions are a parse error that several
verification passes failed to catch, and `KEY_RETURN`/`KEY.RETURN` not
resolving consumed real effort before landing on a magic keycode
workaround. None of this is really about the simulation being unsuited to
Godot — the simulation itself is a plain grid/turn-loop with no real
rendering demands. Python removes the engine-specific friction while
keeping pygame as a normal, well-documented dependency for the parts that
do need 2D rendering (replay viewer, map editor).

This is a **port**, not a rewrite-with-improvements: the simulation rules,
scoring formulas, bot stats, and JSON formats are taken as ground truth
from the Godot source and matched exactly, verified by running real
matches and comparing outcomes (see changelog.md), not by re-deriving the
rules from the design docs alone.

---

## 2. Mapping Godot constructs to Python

| Godot/GDScript | Python | Why |
|---|---|---|
| `Vector2i` | `(int, int)` tuple | No built-in 2D int vector in Python; a tuple is hashable, comparable, and needs no new dependency. |
| `Rect2i(position, size)` | `(x, y, w, h)` tuple | Same reasoning; kept as a flat 4-tuple rather than introducing a Rect class. |
| `RefCounted` data classes (`MapData`, `NanoBotData`, ...) | plain Python classes | No reference-counting concern in Python; ordinary classes suffice. |
| `class_name X` global registration | normal module-level imports | Python's import system doesn't have Godot's "global class cache" failure mode at all — there's nothing to rebuild. |
| Godot `Signal` (used by `TournamentRunner`) | plain callback attributes (`self.on_progress_updated = fn`) | Simplest equivalent; Python has no built-in signal/slot system and adding one (e.g. via a pub-sub library) would be a dependency for no real benefit at this scale. |
| `load(path) as GDScript` + `.new()` for strategy loading | `importlib.util.spec_from_file_location` + scan module attrs for a `NanoStrategy` subclass | Both are "load arbitrary user code from a file path at runtime"; Python's importlib is the direct equivalent. |
| Godot `Thread` (tournament background run) | `threading.Thread` | Direct equivalent; same caveat about marshalling UI updates back to the main thread applies to both (see tournament_runner.py docstring). |
| `FileAccess` / `JSON.parse_string` / `JSON.stringify` | `open()` / `json.load` / `json.dump` | Direct equivalents. |
| Godot `Control` node + `_draw()` + `_input()` | a plain Python class with `draw(surface)` / `handle_event(event)` methods, driven by a `pygame` main loop | pygame has no scene tree or node system — the editor/viewer/menu are just objects the app's `main.py` loop calls into each frame. |

---

## 3. Architecture decisions that differ from the Godot version, deliberately

### One MapData class, not two (MapData + MapDocument)

The Godot map editor (before its v0.0.3 cleanup) had a separate
`MapDocument` class in the editor duplicating the shape of the
simulator's `MapData`, and a separate `MapIO` duplicating the
simulator's `MapLoader` — which is exactly how the duplicate-function
parse error happened (two loaders for the same format, in two files,
eventually colliding). This port uses **one** `core.map_data.MapData`
class for both the simulator and the editor, and **one**
`core.map_loader` module owning both `load_from_file()` and the new
`save_to_file()`/`validate()` (the editor needs save+validate; the
simulator only needs load — but both call into the same module). Editing
operations specific to the map editor (paint, flood-fill, element
placement with duplicate-guards, undo snapshot/restore) live in a
separate `ui/map_editor/map_document_ops.py` as free functions over
`MapData`, rather than wrapping it in a second class.

### Undo snapshots the whole document from the start

The Godot editor's undo system only ever snapshotted `cells`, even though
`save_state()` was called before element (habitas/AZN/zone) mutations
too — so Undo silently never restored a placed/moved/deleted element, in
every commit since that project's Phase 2 (found and fixed in its
v0.0.3). This port's `MapHistory.save_state()` snapshots cells *and*
every element list from the start, verified directly: place a habitas
point, undo, confirm it's gone (see changelog.md).

### AZN quantity editing is inline text entry, not a modal dialog

The Godot editor used a `ConfirmationDialog` + `SpinBox` popup. pygame has
no built-in dialog widgets, and building a generic modal dialog system
for one numeric field would be overkill. Instead, pressing Enter while an
AZN node is selected enters an inline "type digits, Enter to confirm,
Escape to cancel" mode rendered directly in the status bar. Same
end-user capability, less code, no dependency on a widget toolkit.

### Tournament progress callbacks fire directly from the background thread

The Godot version used `call_deferred()` to marshal `Signal` emissions
back to the main thread before touching any UI state from the worker
thread. This port's `TournamentRunner` calls `self.on_progress_updated(...)`
etc. directly from the worker thread (Python's GIL makes individual
attribute reads/writes atomic enough not to crash, but a frame could in
principle render a half-updated count). Accepted as a known simplification
for a progress display, not a correctness-critical path — flagged here
rather than left silent.

---

## 4. What was verified, and how

Every layer was driven with real inputs and real output inspected before
moving to the next layer, rather than written and trusted on inspection
alone — this is the same discipline the Godot project's v0.0.3 cleanup
established after finding that inspection-only verification had let a
parse-breaking bug ship undetected for several commits. See
`changelog.md` for the specific checks; summarized:

- Core simulation: ran real 1500-turn matches via the actual `SimulationCore`, confirmed performance (≤0.1s, far under the 5s requirement), confirmed scoring (a strategy that builds a NanoNeedle and delivers AZN scores >0, one that doesn't scores 0).
- Headless runner: invoked as a real CLI subprocess (`python run_headless.py --map ... --strategy_a ... --strategy_b ...`), not just called as a function.
- Tournament runner: ran a real round-robin via `python run_tournament.py`, confirmed the leaderboard correctly ranks the stronger strategy.
- Map editor: drove it with synthetic pygame events end-to-end (paint, place/duplicate-guard/undo, drag-place a zone, resize a zone corner, edit an AZN quantity, save+reload a map) — this is also where a real bug was caught (sidebar and canvas rects overlapping, causing clicks meant for the canvas to be swallowed by sidebar buttons underneath) and fixed.
- Full app: rendered every screen (main menu, map editor, playback viewer with bot inspector, tournament screen with completed leaderboard) to actual pixel buffers via SDL's dummy video driver and saved them as PNGs, then visually inspected the images — not just confirmed "no exception was raised."
