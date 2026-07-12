# v0.0.18 — Bot Documentation Analysis

**Status:** Complete
**Depends on:** [../v0.0.17/changelog.md](../v0.0.17/changelog.md)

---

## 1. Trigger

"can you help me have an extended explanation of each of the bots and
how to program them on the guide. Also on the simmulation for each bot
have a on sentence explanation of the bot so it is easy to understand
what it does."

Two audiences, two artifacts:

1. **Participants reading the guide** had stat cards (numbers + two
   lines of role text) but nothing connecting a bot to the actual API
   calls that drive it — which calls it responds to, from where, with
   what preconditions.
2. **Spectators watching a match** could click a bot and see its HP
   and position, but nothing saying what a "NanoBlocker" *is*.

## 2. Semantics were verified against the engine, not from memory

Before writing a word, every claim was checked in
`simulation_core.py`'s action handlers and `bot_proxy.py` — several
would have been easy to get subtly wrong:

- `collect_from` / `transfer_to` require **standing on the target
  cell** (`bot.position == target`); there is no acting at range. Both
  move 5 AZN/turn (the `transfer` stat).
- Transfers land in **any friendly bot with capacity** (needle 100,
  container 60, collector 20), or — standing in any of your injection
  zones, including `open_ip()` depots — into the **bank** that pays
  for builds.
- `defend()` needs `max_damage > 0` (collector only), range 12
  **Euclidean**, blocked by Bone and alive NanoWalls, 1–5 random
  damage, and also hits white cells.
- `build()`: NanoAI only, Manhattan distance exactly 1, passable cell,
  paid from bank, lands the same turn **before** combat — the fact
  that makes reactive walls work.
- `open_ip()`: IPCreator only, creates a **permanent** 1×1 zone that
  survives the creator; idempotent per cell.
- One action per bot per turn, **last call wins**; re-issuing orders
  every turn is the intended idiom (`move_to` caches its path).
- First-draft code snippets used `map_info.is_passable(...)` and
  `enemy.position` — neither exists (`get_cell().is_bone` and
  `enemy["position"]` are the real API); both fixed before shipping.
  The docs now show only calls a participant can paste.

## 3. Design decisions

- **Guide**: the stat cards stay (quick reference); a new
  "Programming each bot" section follows with one subsection per bot —
  role, exact preconditions, proven patterns from the shipped demos
  (watchtower, relay, reactive wall), and a paste-ready snippet for
  the five bots whose usage isn't a single obvious call. Two shared
  rules get callouts: last-call-wins, and the golden rule of logistics
  (stand on the cell).
- **Viewer**: the one-sentence descriptions live in
  `data/bot_types.json` next to the stats — one source of truth for
  everything the UI says about a bot type — exposed via
  `bot_type_registry.get_description()`. The Bot Inspector shows the
  sentence (wrapped, max 3 lines) between the type name and the
  stats. The panel grows by 42px **only while a bot is selected**, so
  the Events ticker (which clips to the inspector top since v0.0.15)
  keeps its space the rest of the time.

## 4. Verified

330 tests pass (registry tolerates the new key by construction —
`get_type` returns the raw dict and all stat reads use `.get`).
Scripted check: all 8 types have a sub-130-char sentence, the panel
grows only when selected, the sentence wraps within the 3-line
budget; screenshots inspected at 1280×800 (collector selected,
description + stats, no overflow) and 1024×640 (taller panel cleanly
clips the ticker — no overlap). Guide HTML tag-balance checked.
