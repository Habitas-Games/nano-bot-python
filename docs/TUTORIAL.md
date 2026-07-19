# nano-bot Tutorial — build a competitive strategy in 4 stages

> Somewhere past the skin, a treatment is failing. You have 1500 turns
> to get the medicine where it needs to go, and you can't pilot the
> swarm — you write the mind it carries in. Read the full briefing in
> [`LORE.md`](LORE.md); this page gets your first swarm moving.

**Brand new to programming?** Do
[`learn_to_program.html`](learn_to_program.html) first — it teaches Python from zero
using the swarm. This page assumes you can read a `for` loop.

Each stage is a **complete, runnable strategy**. Copy it into
`strategies/my_strategy.py`, run it, watch it, then move to the next.
Every number below was measured by actually running these files — no
hand-waving.

New here? Read [`STRATEGY_API.md`](STRATEGY_API.md) first (it's the whole
API in one page). Then come back.

**Run any stage:**

```bash
python run_headless.py --map maps/bone_maze.json \
    --strategy_a strategies/my_strategy.py \
    --strategy_b strategies/example_strategy.py --seed 5
```

…or launch `python main.py`, pick your file in the match window, and
press **Run Match** to watch it.

---

## Stage 1 — Score at all (plant a needle)

The minimum that puts a number on the board: walk the NanoAI to the
nearest unclaimed Habitas Point and plant a NanoNeedle on it. An empty
needle scores **5 points per turn**.

```python
from nanobot.api.nano_strategy import NanoStrategy


class MyStrategy(NanoStrategy):
    def choose_injection_point(self, map_info):
        return (0, 0)

    def what_to_do_next(self, map_info, my_bots):
        ai = next((b for b in my_bots if b.type == "NanoAI" and b.is_alive), None)
        if ai is None:
            return
        if any(b.type == "NanoNeedle" and b.is_alive for b in my_bots):
            return                                    # already claimed one
        free = [h for h in map_info.habitas_points if h.owner_id == -1]
        if not free:
            return
        pt = min(free, key=lambda h: abs(h.position[0] - ai.position[0])
                                   + abs(h.position[1] - ai.position[1])).position
        if abs(ai.position[0] - pt[0]) + abs(ai.position[1] - pt[1]) == 1:
            if map_info.azn_bank >= 40:               # NanoNeedle costs 40
                ai.build("NanoNeedle", pt)            # build ON the point
        else:
            ai.move_to(pt)
```

**Measured: 15 points** total across the three shipped maps.

Two rules doing the work here: you must be **exactly 1 cell away** to
`build()`, and the needle goes **on** the Habitas Point, not beside it.

---

## Stage 2 — Get an economy (feed the needle)

An empty needle is 5/turn. A needle with AZN in it is **20 + 2 × AZN**
— a full one is 220/turn. So build a NanoCollector, harvest AZN, and
carry it to the needle.

```python
from nanobot.api.nano_strategy import NanoStrategy


class MyStrategy(NanoStrategy):
    def choose_injection_point(self, map_info):
        return (0, 0)

    def what_to_do_next(self, map_info, my_bots):
        ai     = next((b for b in my_bots if b.type == "NanoAI" and b.is_alive), None)
        col    = next((b for b in my_bots if b.type == "NanoCollector" and b.is_alive), None)
        needle = next((b for b in my_bots if b.type == "NanoNeedle" and b.is_alive), None)
        if ai is None:
            return

        # Build order: collector first (it pays for everything), then the needle.
        if col is None and map_info.azn_bank >= 20:
            x, y = ai.position
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                cell = map_info.get_cell(nx, ny)
                if cell is not None and not cell.is_bone:
                    ai.build("NanoCollector", (nx, ny))
                    break
        elif needle is None:
            free = [h for h in map_info.habitas_points if h.owner_id == -1]
            if free:
                pt = min(free, key=lambda h: abs(h.position[0] - ai.position[0])
                                           + abs(h.position[1] - ai.position[1])).position
                if abs(ai.position[0] - pt[0]) + abs(ai.position[1] - pt[1]) == 1:
                    if map_info.azn_bank >= 40:
                        ai.build("NanoNeedle", pt)
                else:
                    ai.move_to(pt)

        # Collector loop: haul AZN to the needle, else go mine more.
        if col is not None:
            node = min((n for n in map_info.azn_nodes if n.quantity > 0),
                       key=lambda n: abs(n.position[0] - col.position[0])
                                   + abs(n.position[1] - col.position[1]), default=None)
            if needle is not None and col.azn >= 10:
                if col.position == needle.position:
                    col.transfer_to(needle.position)   # must be STANDING on it
                else:
                    col.move_to(needle.position)
            elif node is not None:
                if col.position == node.position:
                    col.collect_from(node.position)    # must be STANDING on it
                else:
                    col.move_to(node.position)
```

**Measured: 640 points — a 43× improvement over Stage 1.**

The golden rule to internalise: `collect_from()` and `transfer_to()`
only work while the bot is **standing on** the target cell. There is no
acting at a distance.

---

## Stage 3 — Survive an attacker (the biggest jump you'll make)

Stage 2 looks great until someone shoots it. Measured against
`example_combat`:

| | vs example_combat |
|---|---|
| Stage 2 (no defense) | **0 / 24 wins** |
| Stage 3 (defended) | **20 / 24 wins** |

A pure economy is a free kill. Defense needs three pieces working
*together* — none of them works alone (measured: wall-only and
shoot-only both still lose 0/24):

1. **Vision** — a NanoExplorer (scan 30) parked on the needle. Under fog
   of war you only see enemies inside a friendly bot's scan radius, and
   everything except the Explorer is nearly blind while a raider shoots
   from 12 cells away.
2. **A reactive wall** — when a raider is spotted, the NanoAI drops a
   NanoWall on the firing line. Builds resolve *before* attacks, so the
   wall beats the shot.
3. **Shooting back** — your collector is the only bot with a gun.

All three ship as a reusable mixin, so you don't have to write the
geometry:

```python
from nanobot.api.nano_strategy import NanoStrategy
from nanobot.api.reactive_defense import ReactiveDefenseMixin


class MyStrategy(ReactiveDefenseMixin, NanoStrategy):   # <-- inherit the mixin
    def choose_injection_point(self, map_info):
        return (0, 0)

    def what_to_do_next(self, map_info, my_bots):
        ai     = next((b for b in my_bots if b.type == "NanoAI" and b.is_alive), None)
        col    = next((b for b in my_bots if b.type == "NanoCollector" and b.is_alive), None)
        needle = next((b for b in my_bots if b.type == "NanoNeedle" and b.is_alive), None)
        if ai is None:
            return

        if col is None and map_info.azn_bank >= 20:
            x, y = ai.position
            for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                cell = map_info.get_cell(nx, ny)
                if cell is not None and not cell.is_bone:
                    ai.build("NanoCollector", (nx, ny))
                    break
        elif needle is None:
            free = [h for h in map_info.habitas_points if h.owner_id == -1]
            if free:
                pt = min(free, key=lambda h: abs(h.position[0] - ai.position[0])
                                           + abs(h.position[1] - ai.position[1])).position
                if abs(ai.position[0] - pt[0]) + abs(ai.position[1] - pt[1]) == 1:
                    if map_info.azn_bank >= 40:
                        ai.build("NanoNeedle", pt)
                else:
                    ai.move_to(pt)
        else:
            # Needle is up: the mixin now drives the AI — it builds the
            # watchtower, then drops reactive walls, then garrisons.
            self.run_defense_ai(map_info, ai, needle, my_bots)

        if needle is not None:
            self.park_watchtower(map_info, my_bots, needle)   # keep vision on the needle

        if col is not None:
            if self.shoot_back(map_info, col):
                return                                        # raider in range: fire instead
            node = min((n for n in map_info.azn_nodes if n.quantity > 0),
                       key=lambda n: abs(n.position[0] - col.position[0])
                                   + abs(n.position[1] - col.position[1]), default=None)
            if needle is not None and col.azn >= 10:
                if col.position == needle.position:
                    col.transfer_to(needle.position)
                else:
                    col.move_to(needle.position)
            elif node is not None:
                if col.position == node.position:
                    col.collect_from(node.position)
                else:
                    col.move_to(node.position)
```

That single change takes you from *never* beating an aggressor to
beating it ~83% of the time.

**The honest trade-off:** in a *peaceful* match Stage 3 scores slightly
less than Stage 2 (measured: 590 vs 640) — the watchtower and walls
cost AZN that would otherwise be sitting in your needle. You're buying
insurance. It's worth it against anything that shoots, which is why the
reflex only spends on walls when a raider is actually spotted rather
than keeping a permanent fortification up.

---

## Stage 4 — Compete for the top

You now have the shape of a real strategy. What separates the top of
the leaderboard from the middle, roughly in order of payoff:

**Route analysis.** Every simple strategy picks targets by straight-line
(Manhattan) distance. That's only correct on open maps — with real
terrain a node 9 cells away can cost *more* to reach than one 12 cells
away down a clear corridor (movement costs 2/3/4 turns per cell by
density, ∓2 on bloodstreams). Running your own Dijkstra over
`map_info.get_cell(...)` to pick the genuinely cheapest target beats the
straight-line guess. Two traps when you do: measure from a **stationary**
origin (your needle) and **commit** to the chosen target, or the ranking
flips every turn as your bot moves and it oscillates without ever
arriving — and cache it, because you have a **50 ms per turn** budget.

**Clear white cells.** `defend()` works on hazards, not just enemy bots,
and they never respawn. ~15–25 turns of collector fire permanently
removes a patrol that would otherwise tax your supply line forever.

**Expand — but only when safe.** Two needles out-score one fortified
needle (double the 20-point base). But two needles can't both be
defended, so expand only while nothing is threatening you. Expanding
under pressure is exactly how a greedy economy loses to an aggressor.

**Know the archetype cycle.** Measured across full tournaments:

```
aggression  beats  greedy economy  beats  turtle defense  beats  aggression
```

There is no single best plan — pick one and cover its weakness.

`strategies/example_adaptive.py` implements all of the above and tops
the tournament; read it once you've got Stage 3 working.

---

## Where to go next

- [`STRATEGY_API.md`](STRATEGY_API.md) — complete API reference.
- `participant_guide.html` — mechanics in depth (fog, hazards,
  line-of-sight, scoring, map making).
- `strategies/` — one focused demo per mechanic; see the guide's list.
- Debugging: if your bots freeze, check the match window's **Events**
  panel — crashes and 50 ms overruns are reported there with the
  exception.
