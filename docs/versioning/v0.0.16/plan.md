# v0.0.16 — Map Pool Rework Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Generate-and-verify before delete: the new map is created and passes
all its gates first, references are repointed, and only then are the
old files removed — the pool is never in a broken intermediate state
for longer than one commit.

## Order

1. **Generate `maps/heart_chambers.json`** by script with hard gates
   (validate, passability of every referenced cell, dual-spawn
   pathfinder reachability of every objective, directional-circuit
   cost check, full round-trip) — the file is only written if every
   gate passes.
2. **Repoint references**: tournament-runner tests (3× simple_tissue,
   1× both-map list → bone_maze + heart_chambers), headless-runner
   tests (2×), README example, `run_headless.py` /
   `headless_runner.py` docstrings.
3. **Annotate historical comments** citing the removed maps as
   confirmed-bug evidence (simulation_core, example_strategy_v2,
   test_simulation_core): "(shipped until v0.0.16)" — keep the
   evidence, date the artifact.
4. **Docs**: MAP-01 sizes, MAP-07 rewritten (Revision 3 note dropping
   the "at least 3 maps" target), GAME-02/GAME-05 map lists,
   participant guide white-cell section.
5. **Delete** `maps/simple_tissue.json`, `maps/vascular_network.json`.
6. **Pool verification**: full pytest; round-robin tournament over the
   two-map pool with zero-score scan (v0.0.10 invariant) and
   hazard-bite counts; showcase match on the new map; screenshots in
   viewer + editor.
7. **Changelog** with the measured results; commit.

## Explicit non-goals

- Strategy/engine changes — if the tournament shows a strategy
  collapsing *only* because of the pool change, that's a finding to
  report, not to silently patch in this version.
- Editor hazard tool (MAP-08) — unchanged.
