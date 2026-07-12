# v0.0.16 — Map Pool Rework Analysis

**Status:** Complete
**Depends on:** [../v0.0.15/changelog.md](../v0.0.15/changelog.md)

---

## 1. Trigger

"bone maze is the only good map delete the others and create a
complete new" — a curation call: Bone Maze stays, Simple Tissue and
Vascular Network go, and one completely new map replaces them.

## 2. Why the old maps were weak (post-hoc, but it checks out)

- **Simple Tissue** was the v0.0.1 bring-up map: near-uniform terrain,
  no hazards, no chokepoints — nothing to route around, so every match
  on it was a straight economy race. It predates every mechanic that
  makes the game a game (fog, hazards, LOS).
- **Vascular Network** had streams and (since v0.0.14) two patrols,
  but its structure was accidental rather than designed — its
  best-known contributions to the project were bugs it exposed (the
  sealed spawn corner behind v0.0.10/v0.0.12 and the boxed-in NanoAI
  fix in example_strategy_v2). The comments recording those findings
  stay, marked "(shipped until v0.0.16)" — the evidence trail outlives
  the map.
- **Bone Maze** was the first map *designed* against the mechanics
  (corridors force LOS decisions, patrols guard lanes, arteries are
  committed fast lanes) — that's the quality bar the replacement has
  to meet.

## 3. The new map: Heart Chambers (60×60)

Distinct character from Bone Maze's concentric labyrinth — where the
maze is about *finding* routes, Heart Chambers is about *committing*
to them:

- **Four muscle chambers** around a **contested central chamber**,
  separated by bone septa. Medium-density bands line the septa and
  high-density cores pad each chamber — terrain cost matters even
  inside a chamber.
- **A one-way clockwise bloodstream circuit** through all four outer
  valves: with the flow it's the fast lane around the heart; against
  it, brutally slow (stream −2/+2 on top of density). Committing to
  the circuit is a real decision, not free travel.
- **Valve chokepoints**: two-cell-wide outer valves where the circuit
  crosses the septa, plus one narrow inner valve per septum arm into
  the central chamber — natural NanoWall/NanoBlocker territory.
- **The central prize**: a habitas point and the richest AZN node
  (40) inside the central chamber, reachable only through the four
  inner valves, guarded by a patrol orbiting the chamber walls. The
  second patrol rides the circuit — the toll on the fast lane.
- **Spawns** in opposite corner chambers (P1 top-left, P2
  bottom-right), 5×5 zones clear of bone.

## 4. Verification approach

Same gates as Bone Maze's generation (v0.0.14), enforced *inside* the
generator — the file is not written unless every check passes:
`validate()` clean; every habitas/AZN/zone/hazard-waypoint cell
passable; every objective pathfinder-reachable from **both** spawn
zones; the circuit measurably cheaper with the flow than against it;
full save/load round-trip (all 3600 cells + hazards field-for-field).

Then pool-level checks: full round-robin tournament over the new
two-map pool with the zero-score scan (the v0.0.10 "every strategy
scores except in needle-kill sieges" invariant must survive the pool
change) and hazard-bite counts on the new map (pressure, not
slaughter). Screenshots of the new map in both the viewer and the
editor. Results in [changelog.md](changelog.md).

## 5. Ripples of deleting two maps

- Tests loaded the real files: tournament-runner failure-isolation
  tests and the headless CLI tests pointed at `simple_tissue.json` /
  `vascular_network.json` — repointed to the surviving pool.
- Docs/examples: README + CLI docstrings used simple_tissue in the
  headless example; MAP-01 (shipped sizes), MAP-07 (map list — the
  "at least 3" target is explicitly dropped as Revision 3: quality
  over count, per the user's call), GAME-02/05 wording; participant
  guide's white-cell section named the old maps.
- Historical code comments citing vascular_network as the map where a
  bug was confirmed stay (the confirmation happened), annotated
  "(shipped until v0.0.16)".
- The main menu's default map (alphabetically first) becomes
  bone_maze.json — already the better first impression.
