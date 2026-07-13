# v0.0.25 — Combat Dethroned Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Order

1. **Make measurement app-faithful** (the v0.0.24 mistake): use
   `winner_id` and the exact `maps × combinations, seed 0..N` schedule.
   Reproduce the user's combat-#1 numbers first.
2. **Head-to-head diagnosis**: confirm combat beats all-but-strategy_v2
   16–0; trace `example_defense` losing 0/24 → 219 attacks, 0 blocked,
   needle dead by T300.
3. **`ReactiveDefenseMixin.needs_defense`**: watchtower-missing or
   threat-present, so strategies can prioritise defense in their build
   order.
4. **`example_defense`**: inherit the mixin for `shoot_back`; drop the
   war-chest banking so the collector stays home to feed the needle
   (walls fund from the starting bank). Measure defense-vs-combat →
   20–12.
5. **`example_ip_creator`**: build the watchtower before the IPCreator
   via `needs_defense`.
6. **Full app-faithful tournament**: confirm defense #1, combat #2,
   top-five spread.
7. **Verify**: pytest, editor check, loader.
8. **Docs**: this folder correcting v0.0.24's over-claim; commit + push.

## Explicit non-goals

- Forcing `container` / `full_roster` / the starter up — their low
  placings are structural to what they demonstrate; documented, not
  tuned away.
- Any engine/scoring/stat change — still pure strategy behaviour;
  wins stay the championship metric.
- Retuning `example_combat` — it's a legitimate strong archetype;
  the fix is that the field now counters it.
