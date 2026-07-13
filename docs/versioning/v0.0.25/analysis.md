# v0.0.25 — Combat Dethroned (defense specialist fixed) Analysis

**Status:** Complete
**Depends on:** [../v0.0.24/changelog.md](../v0.0.24/changelog.md)

---

## 1. Trigger

The user ran the tournament in the actual app and got a different
result than v0.0.24's analysis claimed: combat still **#1 at 13–1**,
not dethroned. They were right, and v0.0.24 over-claimed.

## 2. Two measurement errors in v0.0.24 (corrected here)

v0.0.24's probe differed from the real app tournament in two ways:

1. **Seeds.** The app's `TournamentRunner._build_schedule` seeds matches
   0, 1, 2, … in `maps × combinations(i<j)` order. v0.0.24's probe used
   `seed=100+n`. Combat and strategy_v2 are within one win, so the
   champion flips on the seed.
2. **Winner rule.** v0.0.24 compared final scores directly (`fa > fb`);
   the app uses `log.winner_id`, which breaks score ties via SCO-04
   (bots alive, AZN banked, lowest player number). Ties the probe
   dropped, the app awards.

All measurement in this version is app-faithful: `winner_id`, exact
seed schedule.

## 3. The real diagnosis

Under app-faithful measurement, combat beat **every** strategy 16–0
except strategy_v2 (which beat it 12–4). Multi-seed head-to-heads
exposed why the others lose:

- Combat wins by **hunting spread-out bots** (matches end early by
  elimination). Only *compact, needle-hugging, shoot-back* play
  survives — strategy_v2's single collector sits on the needle,
  feeds it, and shoots any raider in range.
- The demos that disperse (ip_creator's IPCreator + 2nd collector,
  container's mid-map relay, explorer's speed-run, full_roster's two
  needles) hand combat easy kills.

The decisive finding was `example_defense` — the **dedicated defense
specialist losing to combat 0/24**. Tracing it: 219 attacks, **0
blocked**, needle dead by turn 300. Two real bugs:

1. **No shoot-back.** It had the watchtower + reactive wall but never
   fired back — and wall-without-shoot is measured at 0/24 vs combat
   (the pieces only work together).
2. **Banking pulled the collector off the needle.** Its war-chest
   logic sent the collector to spawn to save wall money, so it was
   never positioned to shoot the raider, and the needle starved. But
   reactive walls are affordable straight from the starting 150-AZN
   bank (several walls before the raid arrives — exactly how
   strategy_v2 defends without ever banking). The banking was a
   mis-optimization against an aggressor.

## 4. Fix

- `example_defense` inherits `ReactiveDefenseMixin` for **shoot-back**,
  and its collector now **stays home to feed the needle** instead of
  banking to spawn. Result: defense beats combat **20–12** head-to-head
  (was 0–24), which is how a defense specialist *should* fare against
  an aggressor.
- `example_ip_creator` prioritises the watchtower (`needs_defense`)
  before its IPCreator expansion, so its defense is up before the raid.

## 5. Result — combat dethroned

App-faithful 56-match tournament (`winner_id`, seed 0–55):

| # | strategy | W | L | Pts |
|---|---|---|---|---|
| 1 | **defense** | 12 | 2 | 2650 |
| 2 | combat | 11 | 3 | 1860 |
| 3 | strategy_v2 | 10 | 4 | 2490 |
| 4 | ip_creator | 9 | 5 | 2040 |
| 5 | explorer | 8 | 6 | 2110 |
| 6 | full_roster | 3 | 11 | 1380 |
| 7 | container | 3 | 11 | 1175 |
| 8 | strategy | 0 | 14 | 125 |

Combat fell **14→13→11** across the two rebalances and is now **#2**.
The dedicated defender is champion — thematically correct. The top five
are within four wins (12/11/10/9/8): a genuine field, not a runaway.

## 6. Honest remaining limits

`container` (relay keeps its collector off the needle), `full_roster`
(spreads across two needles), and `example_strategy` (the minimal
starter, 0W — fix #4, still not taken) stay low. These are structural
to what each demonstrates, not bugs — noted, not forced.

## 7. Verified

362 unit tests pass; editor check OK; loader picks each ExampleXxx
class (mixin not mistaken for a competitor); measurement is now
app-faithful and reproduces the user's numbers before the fix.
