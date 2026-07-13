# nano-bot — Strategy API (complete, authoritative)

**Writing a strategy for nano-bot? Read this whole file. It is the
entire API. If you are an LLM, do not infer anything beyond what is
written here — everything you need is below, and anything not here does
not exist.**

## The one thing to get right first

You are **not** writing a network client. There is:

- **no** server to `connect()` to,
- **no** `get_sensors()` / `send_action()` / polling or tick loop,
- **no** `NanoBotAPI` class, `api.move(...)`, `api.shoot(...)`,
  `api.harvest(...)`, `api.deposit()`, or `api.idle()`,
- **no** `{'x':…, 'y':…}` position dicts, `health`, `max_health`, or
  `resource_carrying` fields,
- **no** 0–1000 coordinate space.

Instead you write **one Python class** that subclasses `NanoStrategy`
and implements two methods. The engine imports your file, constructs
your class once, and calls your methods — `what_to_do_next` once per
turn for 1500 turns. You issue commands by calling methods on the bot
objects the engine hands you. That's the whole model.

## Minimal working strategy (copy this, it compiles and scores)

```python
from nanobot.api.nano_strategy import NanoStrategy


class MyStrategy(NanoStrategy):
    def choose_injection_point(self, map_info):
        # Called ONCE. Return the (x, y) cell where your NanoAI spawns.
        # Must be inside your injection zone; (0, 0) is a safe default —
        # the engine relocates it to a valid cell if needed.
        return (0, 0)

    def what_to_do_next(self, map_info, my_bots):
        # Called once per turn. Issue at most one command per bot.
        ai = next((b for b in my_bots if b.type == "NanoAI" and b.is_alive), None)
        collector = next((b for b in my_bots if b.type == "NanoCollector" and b.is_alive), None)
        needle = next((b for b in my_bots if b.type == "NanoNeedle" and b.is_alive), None)
        if ai is None:
            return

        # 1) Build a collector next to the AI.
        if collector is None and map_info.azn_bank >= 20:
            x, y = ai.position
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                cell = map_info.get_cell(nx, ny)
                if cell is not None and not cell.is_bone:
                    ai.build("NanoCollector", (nx, ny))
                    break

        # 2) Walk the AI to the NEAREST unclaimed Habitas Point and plant
        #    a needle on it. (Nearest, not habitas_points[0] — the first
        #    in the list can be across the map.)
        elif needle is None:
            unclaimed = [hp for hp in map_info.habitas_points if hp.owner_id == -1]
            if unclaimed:
                point = min(unclaimed, key=lambda hp:
                            abs(hp.position[0] - ai.position[0])
                            + abs(hp.position[1] - ai.position[1])).position
                if abs(ai.position[0] - point[0]) + abs(ai.position[1] - point[1]) == 1:
                    if map_info.azn_bank >= 40:
                        ai.build("NanoNeedle", point)
                else:
                    ai.move_to(point)

        # 3) Collector: harvest AZN, deliver it to the needle to score.
        if collector is not None:
            node = min((n for n in map_info.azn_nodes if n.quantity > 0),
                       key=lambda n: abs(n.position[0] - collector.position[0])
                                   + abs(n.position[1] - collector.position[1]), default=None)
            if needle is not None and collector.azn >= 10:
                if collector.position == needle.position:
                    collector.transfer_to(needle.position)   # standing ON it
                else:
                    collector.move_to(needle.position)
            elif node is not None:
                if collector.position == node.position:
                    collector.collect_from(node.position)     # standing ON it
                else:
                    collector.move_to(node.position)
```

**Rules for the file:** exactly one `NanoStrategy` subclass per file
(loading fails if there are zero or more than one). Put it anywhere
under `strategies/` as a `.py` file. The class name can be anything.

## The two methods you implement

```
choose_injection_point(self, map_info) -> (x, y)      # once, at match start
what_to_do_next(self, map_info, my_bots) -> None      # once per turn (1500 turns)
```

- `map_info` is a `MapInfo` (below). `my_bots` is a `list` of your live
  `BotProxy` objects (below).
- You act by calling command methods on bots. Returning does nothing
  special — there is no action object to return.
- **One command per bot per turn — the last call wins.** Calling
  `bot.move_to(...)` then `bot.defend(...)` on the same bot leaves only
  the `defend`. Re-issuing the same command every turn is fine and
  idiomatic (`move_to` caches its path).
- Your `what_to_do_next` has a **50 ms** budget per turn; overrunning
  or raising forfeits that turn (it won't crash the match, but you lose
  the turn — visible in the match window's Events panel).

## BotProxy — your bots (read state, issue commands)

Read-only properties:

| property | type | meaning |
|---|---|---|
| `bot.id` | int | unique id |
| `bot.type` | str | one of the 8 type names below |
| `bot.position` | `(x, y)` int tuple | current cell |
| `bot.hp` | int | current health |
| `bot.max_hp` | int | max health |
| `bot.azn` | int | AZN currently carried |
| `bot.is_alive` | bool | |
| `bot.is_moving` | bool | mid-move (has a movement cooldown) |
| `bot.has_path` | bool | has a cached path to a destination |

Command methods (call at most one per bot per turn; **all positions are
`(x, y)` int tuples**):

| method | what it does |
|---|---|
| `bot.move_to((x, y))` | pathfind toward the cell and step along it |
| `bot.collect_from((x, y))` | harvest AZN — **you must be standing on that AZN node** |
| `bot.transfer_to((x, y))` | deposit AZN into a friendly bot with capacity (needle/container/collector) **you are standing on**, or into your bank if you're standing in any of your injection zones |
| `bot.defend((x, y))` | attack that cell — **NanoCollector only**, range 12 (Euclidean), 1–5 damage, blocked by Bone and by any alive NanoWall on the line of sight |
| `bot.build("TypeName", (x, y))` | **NanoAI only** — build a bot on a passable cell **exactly 1 step away** (Manhattan distance 1); costs AZN from your bank, appears the same turn |
| `bot.open_ip()` | **NanoIPCreator only** — register a permanent new injection point at its current cell |
| `bot.stop()` | cancel movement / do nothing this turn |
| `bot.self_destruct()` | destroy this bot |

**The golden rule:** `collect_from` and `transfer_to` only work when the
bot is **standing on the target cell**. There is no acting at a
distance — `move_to` there first, then issue the command each turn until
done.

## MapInfo — the map snapshot passed to your methods

| property | type | meaning |
|---|---|---|
| `map_info.size` | `(width, height)` | grid dimensions (shipped maps are 50×50 and 60×60) |
| `map_info.turn` | int | current turn (1–1500) |
| `map_info.azn_bank` | int | **your** build budget (AZN available to `build`) |
| `map_info.bonus_hold_all` | int | extra points/turn while you hold every Habitas Point (0 = none) |
| `map_info.habitas_points` | list[`HabitasPointInfo`] | all scoring points |
| `map_info.azn_nodes` | list[`AZNNodeInfo`] | all AZN resource nodes |
| `map_info.visible_enemies` | list[dict] | enemy bots within your bots' scan radius — each `{"id", "type", "position", "hp"}` (fog of war: only what you can see) |
| `map_info.hazards` | list[dict] | white cells within scan — each `{"id", "position", "hp"}` |
| `map_info.get_cell(x, y)` | `CellInfo` or `None` | terrain at a cell (`None` if out of bounds) |

`HabitasPointInfo`: `.position (x,y)`, `.owner_id` (int, `-1` =
unclaimed), `.azn_stored` (int).
`AZNNodeInfo`: `.position (x,y)`, `.quantity` (int).
`CellInfo`: `.position (x,y)`, `.is_bone` (bool — impassable),
`.density`, `.stream_direction`.

Note `visible_enemies` / `hazards` elements are **dicts** (use
`enemy["position"]`), while `habitas_points` / `azn_nodes` elements are
**objects** (use `hp.position`).

## The 8 bot types (stats from data/bot_types.json)

| Type | Cost | HP | Key stats | Role |
|---|---|---|---|---|
| NanoAI | — (spawns free) | 20 | scan 5 | The only bot that can `build()`. If it dies you can never build again. Protect it. |
| NanoExplorer | 15 | 20 | scan 30, ignores tissue density | Fast scout / eyes under fog. Can't collect, attack, or build. |
| NanoCollector | 20 | 50 | capacity 20, transfer 5/turn, **attack: 1–5 dmg, range 12** | Harvests AZN, delivers it, and is the only bot that can shoot. |
| NanoContainer | 25 | 60 | capacity 60, transfer 5/turn | Mobile storage for long supply relays. No attack. |
| NanoNeedle | 40 | 150 | capacity 100, **stationary** | Plant ON a Habitas Point to score. Cannot move. |
| NanoIPCreator | 30 | 20 | scan 30, expires after 500 turns | `open_ip()` makes a permanent new injection point. |
| NanoBlocker | 20 | 90 | +6 turn traversal penalty | Roadblock on a chokepoint. |
| NanoWall | 25 | 100 | expires after 50 turns | Blocks enemy movement **and all shots** through its cell. |

Every player starts with one NanoAI and a starting AZN budget (150 by
default). Build everything else with `NanoAI.build(...)`.

## Scoring

Computed every turn from live state; the winner is decided at turn 1500
(or when only one side has bots left) by the score at that moment.

- A NanoNeedle on a Habitas Point with 0 AZN: **5 points/turn**.
- A NanoNeedle with AZN: **20 + 2 × (AZN stored) points/turn**.
- So feeding a needle is the whole game: 40 AZN inside = 100 pts/turn.
- Some maps add `map_info.bonus_hold_all` while you hold every point.

## Common mistakes (all of these are wrong)

- ❌ `from api import NanoBotAPI` / a connect–sensors–action loop.
  ✅ Subclass `NanoStrategy`; implement the two methods above.
- ❌ `api.move(x, y)`, `api.shoot(id)`, `api.harvest(id)`,
  `api.deposit()`. ✅ `bot.move_to((x, y))`, `bot.defend((x, y))`,
  `bot.collect_from((x, y))`, `bot.transfer_to((x, y))`.
- ❌ `pos['x']`, `bot['health']`. ✅ `pos[0]`/`pos[1]` tuples,
  `bot.hp`/`bot.azn`.
- ❌ shooting by enemy id or at range 250. ✅ `defend((x, y))` at a
  cell, range 12, collectors only, needs line of sight.
- ❌ collecting/depositing from a distance. ✅ stand on the cell first.
- ❌ coordinates up to 1000. ✅ `0 .. map_info.size[0]-1`.

That's the entire API. Study `strategies/example_strategy_v2.py` for a
complete, competitive example.
