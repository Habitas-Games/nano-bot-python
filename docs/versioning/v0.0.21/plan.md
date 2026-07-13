# v0.0.21 — SCO-03 Hold-All Bonus Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Data model outward: field + round-trip first, then the engine rule
with tests, then each surface (API, editor, HUD), then content and a
balance run. Same layering as every rules change since v0.0.14.

## Order

1. **MapData**: `bonus_hold_all: int = 0` with the stateless-scoring
   comment. **Loader**: parse (clamped ≥0), serialize only when >0
   (round-trip guard), 4 tests. **Ops**: snapshot/restore include it
   (undo coverage — same trap class as starting_azn in v0.0.2).
2. **Engine** (`_update_scores`): owner-set of `_habitas_state` is
   exactly one real player → add the bonus. 6 tests.
3. **MapInfo**: `bonus_hold_all` attribute set in `build()`.
4. **Editor**: "Starting AZN" section becomes two-row **Map Settings**
   (labels drawn in draw(), value centers shifted on resize);
   `_change_bonus` mirrors `_change_starting_azn` (snapshot →
   undoable, clamp 0–500); per-frame `set_bonus` sync; height re-checked
   at the 640px minimum.
5. **Viewer HUD**: conditional `bonus` layout row (only on bonus
   maps, so no dead space elsewhere); idle text names the prize,
   active text names the collector in their player color.
6. **Content**: Heart Chambers +50 via loader round-trip (validate
   clean, hazards/name intact).
7. **Verification**: full pytest; check_editor; interaction script
   (stepper/undo/dirty/fit/HUD states); 28-match Heart Chambers
   round-robin with bonus-active turn counting.
8. **Docs**: SCO-03 ✅ (Revision 5), M7 milestone ✅ complete, guide
   §6 + §10 + API table, this folder; commit + push.

## Explicit non-goals

- Additional objective types (first-to-X, kill bounties, zone
  control) — wait for a map design that needs one; the JSON-field
  pattern generalizes when it does.
- One-time (non-per-turn) awards — they'd break the stateless
  recompute model for marginal design value.
- Retrofitting a bonus onto Bone Maze — its pocketed-objectives
  layout doesn't point at full-map control the way Heart Chambers'
  contested center does.
