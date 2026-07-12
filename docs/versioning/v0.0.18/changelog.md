# v0.0.18 Changelog

**Version:** 0.0.18
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Bot documentation for both audiences: the participant guide gains an
extended "Programming each bot" section (verified against the engine,
with paste-ready snippets), and the match viewer's Bot Inspector now
shows a one-sentence plain-language description of whatever bot you
click — single-sourced from the bot-stats data file.

## Added — guide (docs/participant_guide.html)

- **"Programming each bot"**: one subsection per bot type after the
  stat cards. Each covers the bot's role, the exact API calls it
  responds to with their real preconditions, and the proven pattern
  from the shipped demo strategies:
  - NanoAI — adjacency-1 building, same-turn builds, why it must live;
  - NanoExplorer — density immunity + Scan 30; sweeping scout and
    needle-watchtower patterns;
  - NanoCollector — harvest/deliver/bank/fight, with the full
    priority-ladder snippet (shoot > deliver > harvest);
  - NanoContainer — the mid-route relay pattern;
  - NanoNeedle — claim mechanics, the 5 vs 20+2×AZN scoring ladder,
    first-claim-holds, live-recomputed score;
  - NanoIPCreator — permanent banking depots that outlive the bot;
  - NanoBlocker — +6 traversal tax on chokepoints, slows white cells;
  - NanoWall — LOS blocking both ways, the 50-turn lifetime economics,
    and the reactive-wall snippet (builds resolve before attacks).
- Two cross-cutting callouts: **one action per bot per turn (last
  call wins; re-issuing every turn is the idiom)** and **the golden
  rule of logistics** (collect/transfer require standing on the
  target cell — nothing works at range).
- Every claim was verified against `simulation_core.py` /
  `bot_proxy.py` before writing; two first-draft snippet APIs that
  don't exist (`map_info.is_passable`, `enemy.position`) were caught
  and corrected to the real ones (`get_cell().is_bone`,
  `enemy["position"]`).

## Added — simulation viewer

- **One-sentence bot descriptions in the Bot Inspector**: click any
  bot and the panel shows what it does in plain language (wrapped,
  up to 3 lines) between the type name and the stats. The sentences
  live in `data/bot_types.json` as a `description` field next to each
  type's stats (`bot_type_registry.get_description()`) — one source
  of truth for everything the UI says about a bot.
- The inspector claims its extra 42px of height **only while a bot is
  selected**, and the Events ticker clips to the same
  `_inspector_top()` — the v0.0.15 no-overlap guarantee holds at
  every window size.

## Verification

```
$ pytest tests/            -> 330 passed
Scripted check: all 8 types have a <130-char sentence; panel grows
  only on selection; descriptions wrap within the 3-line budget.
Screenshots inspected: 1280x800 (collector selected — sentence +
  stats, no overflow) and 1024x640 (taller panel cleanly clips the
  ticker, no overlap).
Guide HTML: tag-balance parse clean.
```

## Known gaps carried forward

- Editor hazard authoring tool (MAP-08 🟡); SCO-03 decision.
