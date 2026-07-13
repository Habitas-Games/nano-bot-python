# v0.0.24 — Strategy Rebalance (economy demos defend) Analysis

**Status:** Complete
**Depends on:** [../v0.0.23/changelog.md](../v0.0.23/changelog.md)

---

## 1. Trigger

Tournament observation: "Combat is the big winner, and the balanced
strategies do bad especially the example_strategy. help me balance
this." The user chose fix **#1** (make the economy demos defend
themselves) over changing the ranking (rejected — "like in the NBA
declaring the champion who made the most points over the season";
wins should crown the champion) and over nerfing the collector
(rejected after confirming the collector's dual economy+attack role is
canon to the original Project Hoshimi).

## 2. Diagnosis (measured, not guessed)

`example_combat` went 14–0. I ruled out every stat/scoring lever by
re-running the 56-match tournament under each:

| Change tested | Combat wins (of 14) |
|---|---|
| baseline | 14 |
| needle HP 150→500 | 14 |
| collector range 12→8, damage 5→3 | 14 |
| unkillable NanoAI | 14 |
| cumulative scoring | 13 |

Robust to all of them. The real cause: combat **hunts and eliminates**
(15/56 matches ended early with the loser wiped to 0 bots by ~turn
275), and the economy demos are **passive** — they build a needle and
feed it but never defend, so they're free kills. `example_defense`
(the one demo that fights back) was already the most combat-resistant,
confirming the fix is defensive behavior, not a rules change.

Isolating the effective reflex (strategy_v2 vs combat, 24 games):

| Reflex | Wins vs combat |
|---|---|
| passive (current) | 0/24 |
| shoot-back only (no vision) | 0/24 |
| watchtower + wall (no shoot) | 0/24 |
| watchtower + shoot (no wall) | 6/24 |
| **watchtower + wall + shoot** | **17/24** |

The three pieces are synergistic — vision is the prerequisite, the
wall buys time, the return fire drives the raider off. None works
alone.

## 3. Implementation

- **`nanobot/api/reactive_defense.py`** — `ReactiveDefenseMixin`
  packaging the proven three-part reflex (`run_defense_ai`,
  `park_watchtower`, `shoot_back`) with self-contained geometry
  helpers. Lives in the `nanobot` package, not `strategies/`, so the
  strategy loader (which only accepts classes *defined in the file*
  and *subclassing NanoStrategy*) never mistakes it for a competitor —
  verified by loading each edited demo.
- Wired into the three passive economy demos: **`example_strategy_v2`,
  `example_container`, `example_ip_creator`** (inherit the mixin, call
  its methods after the needle exists). Left untouched: `example_combat`
  (the aggressor), `example_defense` (already defensive, and the
  reference the mixin distills), `example_explorer` (its Explorer is a
  speed-demo, and it was already competitive at 11W), `example_full_roster`
  (builds its own defense), `example_strategy` (the minimal starter —
  a separate concern).

## 4. Result

56-match tournament, sorted as the leaderboard does (wins, then points):

| # | strategy | W | L | Pts |
|---|---|---|---|---|
| 1 | strategy_v2 | 12 | 2 | 2560 |
| 2 | combat | 12 | 2 | 1600 |
| 3 | ip_creator | 11 | 3 | 2280 |
| 4 | explorer | 9 | 5 | 2170 |
| 5 | defense | 5 | 8 | 1970 |
| 6 | container | 3 | 11 | 1175 |
| 7 | full_roster | 3 | 10 | 1440 |
| 8 | strategy | 0 | 14 | 130 |

Combat fell 14→12 and is **no longer the champion** — a balanced
economy strategy now tops the leaderboard (ties combat on wins, wins
the points tiebreak, out-scores it 60%). `ip_creator` rose 7→11. Early
eliminations fell 15→11. The zero-score cases are all combat matches
(the aggressor eliminating opponents), preserving the v0.0.10
invariant.

`container` stayed low (3W): its collector works the mid-map relay,
away from the needle, so `shoot_back` rarely fires — the watchtower +
wall extend its survival but can't win the collector's duel it's not
present for. That's an honest structural limit of the relay pattern,
not a bug; `container` remains a niche demo. `example_strategy` (the
minimal starter, 0W) is the deliberately-untouched separate concern
(fix #4).

## 5. Verified

362 unit tests pass (mixin import doesn't confuse the loader —
confirmed each demo instantiates its own class); editor check OK;
zero-score invariant holds; win-spread measured before/after.
