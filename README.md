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

**What is this, really?** A treatment is failing somewhere past the skin.
The medicine has to be carried molecule by molecule to receptor sites deep
in living tissue by a swarm too small and too fast to pilot — so you write
the mind it carries in, and let go. The immune system can't tell your bots
from an infection, the bloodstream runs one way, and a rival protocol is in
the same body racing you for the same sites. Full briefing:
[`docs/LORE.md`](docs/LORE.md).

**Never programmed before?** Start with
[`docs/learn_to_program.html`](docs/learn_to_program.html) — eight lessons teaching
Python from zero, ending in a real strategy that wins on every shipped map.

**Know Python already?** Follow [`docs/TUTORIAL.md`](docs/TUTORIAL.md) — four runnable
stages from "plants one needle" to a strategy that beats an aggressor,
with the measured score at every step (Stage 1 → 2 is a 43× jump;
Stage 3 goes from 0/24 to 20/24 against `example_combat`).

> **Using an AI assistant (ChatGPT, Claude, Gemini, …) to write your
> strategy?** Give it [`docs/STRATEGY_API.md`](docs/STRATEGY_API.md) —
> a single, self-contained, plain-text spec of the entire API with a
> verified working example. It's written so an LLM can't invent a
> different API (the participant guide is styled HTML meant for human
> reading, which LLMs consume poorly). Paste that file in, not a link.

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
a NanoCollector and a NanoNeedle, scores points, and defends the needle
against an aggressor (via the shared `ReactiveDefenseMixin` in
`nanobot/api/reactive_defense.py` — a pure economy loop with no defense
is a free kill for a bot-hunting opponent).

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
- `example_full_roster.py` — the two-needle economy powerhouse: claims
  and feeds two Habitas Points to out-score a single-needle turtle,
  deliberately defense-light so an aggressor can punish it (the
  "economy" corner of the strategy rock-paper-scissors).
- `example_adaptive.py` — **the advanced demo (currently top of the
  tournament).** Reacts to what it sees rather than running a fixed
  plan: scouts, defends reactively, clears white cells (nothing else
  does), expands only when safe, and picks targets by true path cost
  (its own Dijkstra) instead of straight-line distance.

The demo strategies form a loose **rock-paper-scissors**: aggression
(`example_combat`) beats the greedy two-needle economy
(`example_full_roster`), which out-scores turtle defense
(`example_defense`), which walls out aggression. No single demo beats
the whole field — see `docs/versioning/v0.0.26/`.

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

## Documentation

Human-facing docs live in two forms, from **one source**:

- **Markdown** (`docs/*.md`) is the source of truth — it renders on
  GitHub, and `STRATEGY_API.md` must stay markdown because its job is
  being pasted into an AI assistant.
- **HTML** (`docs/lore.html`, `tutorial.html`, `strategy_api.html`) is
  what the website links to, because a browser shows raw `.md` as
  unstyled text.

The HTML is generated — never hand-edit it:

```bash
python tools/build_docs.py            # regenerate after editing any docs/*.md
python tools/build_docs.py --check    # fails if the HTML is stale
```

`tests/test_docs_build.py` runs that check, so editing markdown and
forgetting to rebuild fails the suite instead of silently shipping a
stale site. (`participant_guide.html` and `learn_to_program.html` are
hand-written HTML, not generated.)

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/
```

362 unit tests cover the core simulation engine and map-editor logic
(`tests/test_*.py`). The pygame rendering/input layers (renderer, playback
viewer, tool event handling, main menu threading) don't have unit tests
yet — those were verified via scripted integration checks driving real
pygame events headlessly (`SDL_VIDEODRIVER=dummy`) and real CLI runs
instead; see `tests/check_editor.py` and `docs/versioning/v0.0.1/changelog.md`
/ `docs/versioning/v0.0.2/changelog.md` for what was verified and how.
