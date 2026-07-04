# v0.0.13 — Requirements Revision 2, Guide & Site Refresh Analysis

**Status:** Complete
**Depends on:** [../v0.0.12/changelog.md](../v0.0.12/changelog.md)

---

## 1. Trigger

User request: review and update the requirements, and review the
project's UX and fun along with the webpage and participant guide. One
explicit constraint: the design inspiration behind the game is not to be
named anywhere in the project's documents.

## 2. State of the old requirements doc

The previous `docs/requirements.md` was a port-era diff: it named the
original competition in §1 (the one thing the user asked to remove) and
delegated every actual requirement table to the sibling engine port's
requirements file — meaning this project's own spec wasn't
self-contained and hadn't absorbed anything learned or changed across
v0.0.2–v0.0.12 (tie-break rule, `starting_azn`, container transfers,
density immunity, working `open_ip()`, the match-window workspace,
1-indexed labels, random spawn fallback).

## 3. What the rewrite does

Revision 2 is fully self-contained: all requirement tables inlined and
corrected to match verified current behavior, each with an explicit
status (✅/🟡/⬜/❓). Notable corrections against reality: MAP-01's map
sizes (shipped 80×80/60×60, no hardcoded 50×50 default), SIM-02's actual
8-phase turn order, SCO-04's real tie-break (bots alive → banked AZN →
lowest player number, "turns elapsed" documented as deliberately
dropped), BOT-01's actual NanoAI-death behavior (no *new* actions;
in-flight movement completes), BOT-10 generalized transfers, and the
VIS section rewritten around the match-window workspace that exists
today rather than the plain viewer that was originally specced.

## 4. Fun & UX review — how it was grounded

Not a fresh play-test: this session had already generated the evidence.
Every finding in the new §6 traces to something verified earlier by
execution: the 14–0 combat shutouts and the walls-don't-stop-ranged-
attacks confirmation (v0.0.10), the contested-Habitas silent-overwrite
trace (v0.0.8), the fog-of-war "future milestone" note that has sat in
`map_info.py` since v0.0.1 making Scan a dead stat, the GUI's hardcoded
seed 0 (verified by grep this round), the missing third map (MAP-07),
the editor's fixed zone owner, and the absence of any in-app way to
open tournament/headless replays (the guide even claimed a "Load
Replay" picker that doesn't exist — inherited from the sibling port's
guide, where it does).

The one deliberately design-inspiration-informed addition (unnamed in
the doc, per the constraint): **environmental immune-system hazards**.
The theme promises a body that fights back; today the only threat is
the opponent, so most matches are two parallel economies. This is
GAME-02, the highest-impact fun item, specced as data-driven per-map
hazards consistent with NFR-02.

§7 turns the findings into roadmap requirements: GAME-01 (fog of war),
GAME-02 (hazards), GAME-03 (combat counterplay via line-of-sight —
marked ❓, needs a rule decision), GAME-04 (habitas exclusivity — ❓),
GAME-05 (third map), UX-01..04 (replay browser, zone owner selector,
event VFX + menu art, seed control). M6/M7 milestones reframed around
them.

## 5. Guide and site staleness (all verified by grep before editing)

Six stale claims in `docs/participant_guide.html`, one in `index.html`,
two in `README.md` — each one a real behavior change from
v0.0.7–v0.0.11 that the docs (written at v0.0.6) never absorbed:
quickstart pickers described on the main menu (moved to the match
window in v0.0.9), pan documented as middle-drag only (left-drag since
v0.0.7), `transfer_to` documented as needle-or-bank only (containers
since v0.0.8), the starter strategy described as never scoring (scores
since v0.0.10), the tie-break naming "player 0" (labels 1-indexed since
v0.0.11), the nonexistent "Load Replay" picker, README's stale test
count and menu-flow description. Also added: the six demo strategies as
a reading path in the guide's §8 (they existed since v0.0.8 but the
guide never mentioned them).
