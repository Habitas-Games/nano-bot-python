# v0.0.27 — LLM-Consumable Strategy API Spec Analysis

**Status:** Complete
**Depends on:** [../v0.0.26/changelog.md](../v0.0.26/changelog.md)

---

## 1. Trigger

The user gave Gemini "the link of the guide" and asked it to write a
strategy. The result (`strategies/gemini.py`) doesn't work at all —
"that means the guide does not do its job."

## 2. Diagnosis

`gemini.py` didn't get one detail wrong — it invented an **entirely
different game and API**:

- `from api import NanoBotAPI` and a `connect()` / `get_sensors()` /
  `send_action()` network-client loop — the real model is: subclass
  `NanoStrategy`, implement `choose_injection_point` and
  `what_to_do_next(map_info, my_bots)`, called once per turn.
- `api.move(x,y)`, `api.shoot(id)`, `api.harvest(id)`, `api.deposit()`,
  `api.idle()` — none exist; the real commands are `bot.move_to((x,y))`,
  `bot.defend((x,y))`, `bot.collect_from((x,y))`, `bot.transfer_to((x,y))`.
- `{'x':…, 'y':…}` position dicts, `health`/`max_health`/
  `resource_carrying`, a 0–1000 coordinate space — the real API uses
  `(x, y)` int tuples, `hp`/`azn`, and 50–60-cell grids.

The participant guide's **content is correct and complete** (§7 is a
full API reference, §2 has the exact skeleton). So this is not a
content gap — Gemini never actually consumed it. Two compounding
reasons:

1. The guide is a large **styled HTML** file. GitHub serves `.html`
   as escaped source, not rendered; and LLMs parse dense styled HTML
   far worse than plain markdown. Handing over "a link" to it gives an
   LLM little usable signal.
2. Nothing in the guide **forecloses the wrong mental model**. Given
   "AI bot programming game," an LLM's prior is a network client with
   move/shoot/harvest — and nothing said "no, it's not that."

The user's conclusion is right in the way that matters: if handing the
guide to an LLM yields broken code, the guide failed the practical job,
even though its content is accurate.

## 3. Fix

A new **`docs/STRATEGY_API.md`** — a single, self-contained,
plain-markdown spec of the entire API, built to make Gemini's exact
mistakes impossible:

- Opens by explicitly ruling out the wrong model ("you are **not**
  writing a network client; there is no `connect`/`sensors`/tick loop,
  no `NanoBotAPI`, no `{'x','y'}` dicts, no 0–1000 coords").
- A complete minimal strategy that **loads, runs, and scores** —
  verified in-engine on both shipped maps (200 and 220 pts, wins
  both), not just eyeballed.
- Every `BotProxy` property and command method with types and the
  standing-on-the-cell / adjacency / range-12 constraints; the full
  `MapInfo` shape (and the dict-vs-object distinction for
  `visible_enemies` vs `habitas_points`); the 8-bot stat table; the
  scoring formula.
- A "common mistakes (all of these are wrong)" section listing the
  exact hallucinations from `gemini.py` next to the real calls.

The README and the guide's §7 both point to it with the instruction to
**paste the file's contents into the LLM**, not a link.

## 4. Verified

The doc's minimal example was extracted verbatim and run in-engine:
loads as a `NanoStrategy`, and scores on both maps (initially it whiffed
Heart Chambers by targeting `habitas_points[0]`; fixed to nearest
unclaimed point → 200/220, wins both). 362 unit tests still pass
(docs-only + one new markdown file; no code change).
