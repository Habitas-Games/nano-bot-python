# v0.0.29 Changelog

**Version:** 0.0.29 — documentation & tutorial pass

---

## Added — `docs/TUTORIAL.md`

A progressive, four-stage tutorial. Each stage is a complete runnable
strategy, and **every number in it was produced by running the code**:

| Stage | What it adds | Measured |
|---|---|---|
| 1 | Plant a needle | 15 pts (3 maps) |
| 2 | Collector + feed it | **640 pts — 43x Stage 1** |
| 3 | Vision + reactive wall + shoot-back | **0/24 -> 20/24 vs example_combat** |
| 4 | Route analysis, hazard clearing, safe expansion, the archetype cycle | (points at `example_adaptive`) |

Stage 3 also states the honest trade-off: it scores *less* in peaceful
matches (590 vs 640) because defence costs AZN — you're buying
insurance.

Verification: all three code blocks were extracted verbatim from the
markdown, loaded as strategies, and run — they produce exactly the
scores claimed.

## Fixed — stale/missing docs

- **`example_adaptive` was documented nowhere** (guide and README) despite
  being the tournament champion. Now described in both, plus the guide's
  demo list.
- **The guide's `example_full_roster` description was wrong** — it still
  said "all of the above combined: defense, scouting, a forward base, a
  relay, and a fighter." v0.0.26 rewrote it as a deliberately
  defence-*light* two-needle greedy economy. Corrected.
- Demo count corrected ("six more" -> seven).

## Added — strategic content

- The guide now documents the measured **archetype cycle**
  (aggression > greedy economy > turtle defence > aggression) with the
  0/24 vs 20/24 evidence, so readers learn there is no single best plan.
- The landing page gained cards for the tutorial and the AI-assistant
  API spec alongside the guide.

## Verification

```
$ pytest tests/  -> 362 passed
Tutorial code blocks: 3/3 load and run, scores match the doc exactly.
HTML tag-balance: index.html and participant_guide.html both clean.
```
