# nano-bot-python

A turn-based AI programming competition set inside a simulated human body —
**Python + pygame port** of the [nano-bot](../nano-bot) Godot project, for
the same reasons documented in that project's
`docs/versioning/v0.0.3/analysis.md`: Godot/GDScript introduced friction
(class-name resolution, duplicate-function parse errors going undetected,
engine-specific patterns) that a plain Python implementation avoids.

This is a faithful port, not a redesign — the simulation rules, scoring
formulas, bot stats, and JSON map/replay formats are identical to the
Godot version. See `docs/requirements.md` for the full spec.

## What is nano-bot?

Participants write a single Python strategy file controlling a fleet of
nanobots navigating a grid of living tissue. Bots collect AZN energy
molecules, claim **Habitas Points**, and outscore the opponent over 1500
turns. The simulation runs headless at hundreds of matches per second. A
**pygame map editor** lets you design custom tissue layouts. A **pygame
replay viewer** lets you scrub through any match.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py                  # launch the app (main menu)
```

From the main menu: **Run Match** opens the match window. Pick a map and
both strategies with the file-browser buttons at the top (they can browse
anywhere on disk, remember the last folder per type, and restore your
last selections across restarts), then press **Run Match** — the result
opens playing, fitted to the window (Space play/pause, arrows step, F
re-fits, wheel zooms at the cursor; speeds up to 16x). **Map Editor**
opens the visual map editor (Ctrl+S save, Ctrl+Z undo, middle-drag pans
from any tool, and it warns before discarding unsaved changes).
**Tournament** runs a round-robin over competitors you add explicitly
(multi-select supported), across every shipped map, with live standings.

## Writing a strategy

```bash
cp strategies/example_strategy.py strategies/my_strategy.py
```

```python
from nanobot.api.nano_strategy import NanoStrategy

class MyStrategy(NanoStrategy):
    def choose_injection_point(self, map_info):
        return (map_info.size[0] // 2, map_info.size[1] // 2)

    def what_to_do_next(self, map_info, my_bots):
        for bot in my_bots:
            if map_info.habitas_points:
                bot.move_to(map_info.habitas_points[0].position)
```

See `strategies/example_strategy_v2.py` for a fuller example that builds
a NanoCollector and a NanoNeedle and actually scores points.

Beyond those two, `strategies/` has one focused demo per bot type/mechanic
that example_strategy_v2 doesn't touch — each is a complete, runnable
strategy, not a snippet:

- `example_explorer.py` — NanoExplorer's density immunity (it pays flat
  minimum movement cost through any tissue density).
- `example_container.py` — NanoContainer as a two-stage AZN relay
  (collector -> container -> needle).
- `example_defense.py` — NanoBlocker + NanoWall defending a claimed
  Habitas Point's chokepoint.
- `example_combat.py` — defend()/attack, hunting enemy bots in range.
- `example_ip_creator.py` — NanoIPCreator's open_ip(), banking AZN at a
  second injection point far from the original spawn.
- `example_full_roster.py` — all of the above combined into one
  competitive strategy claiming two Habitas Points.

## CLI tools

```bash
# Headless: run one match between two strategies, save a replay
python run_headless.py --map maps/bone_maze.json \
    --strategy_a strategies/example_strategy.py \
    --strategy_b strategies/example_strategy_v2.py \
    --seed 42 --out replays/my_match.json

# Round-robin tournament over everything in strategies/ and maps/
python run_tournament.py
```

## Project layout

```
nano-bot-python/
├── main.py                 # pygame app entry point
├── run_headless.py         # CLI single-match runner
├── run_tournament.py       # CLI round-robin tournament
├── nanobot/
│   ├── core/                # simulation engine — no pygame dependency
│   ├── api/                 # strategy-facing classes (NanoStrategy, MapInfo, BotProxy, ...)
│   ├── runner/               # headless runner implementation
│   ├── tournament/           # round-robin scheduler + leaderboard
│   └── ui/                   # pygame: main menu, map editor, playback viewer, tournament screen
├── data/bot_types.json      # bot stat budgets
├── maps/                     # JSON map definitions
├── strategies/               # participant strategy files
├── replays/                  # auto-saved match logs (gitignored)
└── docs/                     # requirements + versioning history
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/
```

321 unit tests cover the core simulation engine and map-editor logic
(`tests/test_*.py`). The pygame rendering/input layers (renderer, playback
viewer, tool event handling, main menu threading) don't have unit tests
yet — those were verified via scripted integration checks driving real
pygame events headlessly (`SDL_VIDEODRIVER=dummy`) and real CLI runs
instead; see `tests/check_editor.py` and `docs/versioning/v0.0.1/changelog.md`
/ `docs/versioning/v0.0.2/changelog.md` for what was verified and how.
