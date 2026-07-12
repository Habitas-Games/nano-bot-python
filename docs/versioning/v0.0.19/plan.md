# v0.0.19 — Map Editor Completion Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Data layer first (ops + loader with unit tests), then the tool, then
the chrome (sidebar/modals), then a single interaction script that
walks the full authoring story — the same layered order as v0.0.14.

## Order

1. **Ops** (`map_document_ops.py`): `add_hazard` (passability-gated,
   move_every floored at 1), `find_hazard_at` (any waypoint),
   `delete_hazard`; fix `clear_all()` leaking hazards. +8 tests.
2. **Loader** (`map_loader.py`): `validate()` gains passability checks
   (habitas/AZN/zone/hazard-waypoint); `derive_map_name()`. +7 tests.
3. **HazardTool** (`tools/hazard_tool.py`): pending-path state,
   left-click add / right-click-or-Enter commit / Backspace undo-point
   / 1-2-3 speed / right-click-existing delete; status text narrates
   each mode; crosshair cursor; pending cleared on tool switch.
4. **Renderer**: `pending_hazard` kwarg — numbered green waypoints +
   polyline, distinct from committed patrols' white.
5. **Sidebar**: 4th Elements button (new `white_cell_icon`), Starting
   AZN header + stepper (−25/+25, value drawn from a per-frame synced
   display), New+Load sharing one row (height budget), callbacks
   `on_new`/`on_azn_delta`; resize shifts the value center too.
6. **Editor screen**: tool registration + icon map; `_create_new_map`
   (spec parsing with friendly errors, 10–200 clamp) behind a
   `new_map` modal; `confirm_discard` generalized with `next:
   "load"|"new"`; `_change_starting_azn` as a snapshotted edit;
   `_do_save` stamps the derived name; per-frame starting-AZN sync.
7. **Verification**: full pytest + check_editor; 26-check interaction
   script (real events end-to-end); screenshots (pending path + new
   sidebar, New Map dialog, 640px fit); guide HTML parse.
8. **Docs**: guide section 10 "Creating your own maps" + TOC entry;
   MAP-08 → ✅ and the M7 milestone line; this folder; commit + push.

## Explicit non-goals

- Per-patrol stat editing UI (hp/damage/range) — speed is the knob
  that shapes gameplay geography; the rest are rare tweaks with a
  documented JSON escape hatch. Revisit if map authors actually ask.
- Redo (the undo stack stays single-direction, 50 deep).
- Waypoint-level editing of committed patrols (delete + redraw is the
  flow; patrols are seconds to author).
