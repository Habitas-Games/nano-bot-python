# v0.0.26 — Strategy Rock-Paper-Scissors Analysis

**Status:** Complete
**Depends on:** [../v0.0.25/changelog.md](../v0.0.25/changelog.md)

---

## 1. Trigger

After v0.0.25 dethroned combat, the user ran the tournament and saw
defense on top: "now defense is the big winner." Correct — I had only
moved the crown, not removed it.

## 2. The structural finding

I built the full head-to-head matrix. It exposed the real problem: the
game was a **linear dominance ladder, not a cycle**. `defense` lost to
*nobody*; `strategy_v2` lost to nobody either; `combat` lost only to
those two; the bottom three lost to everyone above. Whoever defended
their needle best simply won.

Root cause: **reactive defense is nearly free** (a one-time 15-AZN
watchtower; walls only when attacked), so "economy + free defense"
(defense) strictly beats "economy alone." Per-strategy tuning can only
relocate the crown, never remove it — which is exactly what v0.0.24/25
did (combat → defense).

## 3. What was missing

A genuine rock-paper-scissors needs three edges. Two already existed:

- aggression (`combat`) beats undefended/spread economy ✓
- turtle defense (`defense`) beats aggression ✓
- **greedy economy should beat turtle defense — it didn't.**

The third edge requires an economy that *out-scores* a turtle. Since
score is a per-turn snapshot of needles held, the way to out-score one
fortified needle is to hold **two** (double the 20-point base plus AZN
across both). Two needles also can't both be defended, so an aggressor
punishes them — which supplies the "combat beats economy" edge too.
`example_full_roster` was nominally the two-needle strategy but badly
implemented (3W, lost to everyone).

## 4. Implementation

Rewrote `example_full_roster` as the **greedy two-needle economy**:
claim and feed the two nearest Habitas Points with two collectors,
deliberately **defense-light** (no walls, no watchtower — being
beatable by aggression is its role), keeping a one-needle **build
reserve** (40 AZN, banked at the spawn injection zone) so a needle lost
to a raider or a contested node is reclaimed rather than left down a
point. Its old "all 8 bot types" showcase is dropped — each bot type
is already demonstrated by a focused demo, and a real archetype is
worth more to the meta than a mediocre kitchen sink.

Prototype verification before committing: the two-needle economy beats
`defense` on open Heart Chambers (2 needles at 70 AZN = 320 pts/turn vs
the turtle's single needle at 220) and loses to `combat` 0/24
everywhere.

## 5. Result — no strict king

App-faithful 56-match tournament (`winner_id`, seed 0–55):

| # | strategy | W | L | Pts |
|---|---|---|---|---|
| 1 | defense | 11 | 3 | 2650 |
| 2 | combat | 11 | 3 | 1720 |
| 3 | strategy_v2 | 9 | 5 | 2500 |
| 4 | ip_creator | 8 | 6 | 2030 |
| 5 | full_roster | 7 | 7 | **2760** |
| 6 | explorer | 7 | 7 | 2110 |
| 7 | container | 3 | 11 | 1175 |
| 8 | strategy | 0 | 14 | 130 |

**No strategy beats the whole field** (the strict-king check is empty —
was `defense` in v0.0.25). full_roster went 3→7W and is the top
*scorer*; its record is the economy archetype exactly — loses to combat
(0–2), ties everyone else. The lead is a two-archetype tie
(defense/combat at 11), not one dominant strategy, and it is
seed/map-sensitive.

The economy-beats-turtle edge is **map-dependent** (economy wins on
open Heart Chambers, the turtle wins in Bone Maze's corridors) — kept
deliberately: different maps favouring different archetypes is good
balance, not a bug.

## 6. Honest limits

`container` (relay keeps its collector off the needle) and
`example_strategy` (the minimal starter, 0W — the untaken fix #4) stay
low; structural to what they are, documented, not forced.

## 7. Verified

362 unit tests pass; editor check OK; loader instantiates the rewritten
`ExampleFullRoster`; full head-to-head matrix confirms no strict king;
measurement app-faithful.
