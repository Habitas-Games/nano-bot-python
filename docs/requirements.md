# Nano-Bot Simulation Platform — Requirements (Python port)

Adapted from the Godot project's `docs/requirements.md`. The simulation
rules, scoring, bot stats, and JSON formats are unchanged — only the
implementation language and rendering library differ (GDScript/Godot →
Python/pygame). Where a requirement below differs from the original, the
difference is called out explicitly.

## 1. Overview

A simulation platform inspired by Microsoft Imagine Cup's **nano-bot**.
Participants write AI strategies that control teams of nanobots navigating
a human-body-themed grid world. Strategies compete head-to-head in a
turn-based simulation, with a built-in pygame viewer, scoring system, and
tournament bracket.

## 2. Goals

| # | Goal |
|---|---|
| G1 | Participants submit a Python strategy file — no game engine knowledge required. |
| G2 | Two or more strategies can battle simultaneously on the same map. |
| G3 | The simulation runs headlessly (no rendering) for fast batch evaluation. |
| G4 | A pygame visual playback mode lets anyone watch a match replay step by step. |
| G5 | A tournament mode runs all submitted strategies against each other and produces a ranked leaderboard. |

## 3. Scope

Same as the Godot version's §3 — grid map engine, all 8 nanobot types,
turn-based simulation (≤1500 turns), Python strategy API, 2D top-down
visual player, scoring per the original nano-bot rules, 1v1+ tournament
runner, JSON match export. Out of scope: 3D visualization, networked
multiplayer, a strategy IDE, full script sandboxing, mobile/web export.

**Difference from Godot version:** there is no load-time sandboxing
equivalent to GDScript's "no `get_tree()`/`get_node()` calls" check
(STR-06 in the original). A Python strategy file is `exec`'d directly via
`importlib`, so it can technically import anything the interpreter can.
This is accepted as out of scope for the same reason the original called
out "no anti-cheat / full script sandboxing" — both versions trust the
strategy author.

## 4. Functional Requirements

All requirement IDs (MAP-01..07, BOT-01..10, STR-01..07, SIM-01..09,
SCO-01..05, VIS-01..08, TRN-01..05) carry over unchanged from the Godot
version's requirements.md §4 — see that file for the full tables. The
only textual changes are:

- STR-01: "a single `.py` file that subclasses `NanoStrategy`" (was `.gd` / `extends`).
- STR-02: method names are `choose_injection_point(map_info)` and
  `what_to_do_next(map_info, my_bots)` — identical signatures, Python
  syntax (`def`, type hints optional).
- STR-04: positions are plain `(x, y)` tuples, not `Vector2i` — Python has
  no built-in 2D integer vector type, and introducing a custom one would
  add a dependency for no benefit over a 2-tuple.
- STR-06 is dropped per the scope note above.

## 5. Non-Functional Requirements

Same as the Godot version's §5, with NFR-03 ("Portability") changed from
"runs on Linux, Windows, and macOS via Godot 4.x export" to "runs anywhere
Python 3.10+ and pygame run" — i.e. the same three platforms, via a
different mechanism (no compiled export step; just `pip install -r
requirements.txt`).

## 6. Strategy API Reference

```python
from nanobot.api.nano_strategy import NanoStrategy

class MyStrategy(NanoStrategy):
    def choose_injection_point(self, map_info):
        # Return an (x, y) tuple within your injection zone.
        return (0, 0)

    def what_to_do_next(self, map_info, my_bots):
        # Queue actions on bots via BotProxy methods.
        pass
```

### MapInfo (read-only)

```python
map_info.size                  # (width, height)
map_info.get_cell(x, y)        # CellInfo(density, stream_direction, is_bone) or None
map_info.habitas_points        # list[HabitasPointInfo]  .position .owner_id .azn_stored
map_info.azn_nodes             # list[AZNNodeInfo]        .position .quantity
map_info.visible_enemies       # list[dict]               {id, type, position, hp}
map_info.turn                  # int, current turn number
map_info.azn_bank               # int, this player's banked AZN
```

### BotProxy (action queue — last call per turn wins)

```python
bot.type; bot.position; bot.hp; bot.azn; bot.is_alive
bot.move_to(target)
bot.collect_from(node_position)
bot.transfer_to(target_position)
bot.defend(enemy_position)
bot.build(bot_type, position)
bot.open_ip()
bot.stop()
bot.self_destruct()
```

## 7. File & Folder Structure

See `README.md` for the current layout.

## 8. Milestones

| Milestone | Status |
|---|---|
| M1 — Core Engine (map, simulation loop, 8 bot types, pathfinding, scoring) | Done — see `docs/versioning/v0.0.1/changelog.md` |
| M2 — Strategy API (NanoStrategy, MapInfo, BotProxy, example strategies) | Done |
| M3 — Visual Playback (match log recorder, pygame renderer, controls, HUD) | Done |
| M4 — Tournament (round-robin runner, leaderboard, JSON export) | Done |
| M5 — Map Editor (pygame port of the Godot v0.0.3 editor architecture) | Done |
| M6 — Polish (more maps, packaging, automated test suite) | Not started |
