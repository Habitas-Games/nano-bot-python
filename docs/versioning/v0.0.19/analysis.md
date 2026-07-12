# v0.0.19 — Map Editor Completion Analysis

**Status:** Complete
**Depends on:** [../v0.0.18/changelog.md](../v0.0.18/changelog.md)

---

## 1. Trigger

"on the map creator can I add enemies?" (answer: no — MAP-08's carried
gap) followed by "Help me complete the map creator please with anything
missing", plus "the docs html are not clear on this either" — the guide
had no map-creation documentation at all (the word "editor" appeared
nowhere in it).

## 2. Audit: editor vs everything a map JSON can express

| Map JSON field | Before v0.0.19 |
|---|---|
| cells (terrain/streams) | ✅ paintable |
| habitas_points | ✅ tool |
| azn_nodes + quantities | ✅ tool + Edit-Enter quantity entry (existed but was undocumented) |
| injection_zones + owner | ✅ tool + P1/P2 toggle |
| **hazards** | ❌ rendered read-only; authored only by hand-writing JSON |
| **starting_azn** | ❌ round-tripped since v0.0.2 but no UI to change it |
| **width/height** | ❌ no New Map — stuck with the loaded map's size |
| name | ⚠️ every new map saved as "Untitled Map" — and the name is the replay→map resolution key, so duplicates make replays ambiguous |

Plus two latent defects found during the audit:
- **Clear Map leaked hazards** — `clear_all()` cleared every element
  list except `hazards`, so "cleared" maps silently carried the old
  patrols into their next save.
- **validate() ignored placement sanity** — objectives on Bone, fully
  boned zones, and boned patrol waypoints all passed validation and
  produced broken matches instead of save-time errors.

## 3. Design

- **White Cell tool** (Elements row, blob icon): left-click lays
  waypoints (live numbered green preview, refusing impassable cells),
  right-click/Enter commits (one waypoint = stationary guard),
  Backspace removes the last point, keys 1/2/3 set patrol speed.
  With nothing pending, right-clicking an existing patrol's waypoint
  deletes it. Combat stats use the shipped maps' proven defaults
  (hp 45 / damage 3 / range 1.5) — the tool owns *where patrols roam*
  (the part that was impossible without coordinates by hand); rare
  stat tweaks stay in JSON, documented in the guide.
- **New Map**: size dialog ("60x60", clamped 10–200 per side), guarded
  by the same confirm-discard flow as Load (generalized with a `next`
  field). Shares a sidebar row with Load — the panel is near its
  height budget at the 1024×640 minimum (fits with 38px to spare).
- **Starting AZN**: −25/+25 stepper in the sidebar; changes are real
  document edits (snapshotted → undoable, dirty-tracked); display
  synced per-frame like the Undo button, so undo updates it too.
- **Save naming**: every save stamps `map_name` derived from the
  filename (`marrow_gauntlet.json` → "Marrow Gauntlet") via a new
  `map_loader.derive_map_name()` — no more "Untitled Map" pileups.
- **validate() upgrades**: impassable habitas/AZN/waypoint cells and
  zero-passable-cell zones are errors, surfaced by the existing
  save-anyway dialog.
- **Docs**: the guide gains section 10, "Creating your own maps" —
  tool table (including the previously undocumented Edit-Enter AZN
  quantity entry and Ctrl shortcuts), map-design guidance (mirrored
  spawns, chokepoints, patrol pressure), the hazard stat defaults and
  their JSON escape hatch, and the save/play loop including headless
  side-swap testing.

## 4. Verified

345 unit tests (+15: hazard ops, clear-all leak, validate passability,
name derivation); `check_editor.py` ALL OK; a 26-check interaction
script drove the full authoring story with real events (sidebar button
→ waypoints → bone refusal → speed key → commit → undo → delete →
AZN stepper undo → dirty-guarded New → size parsing incl. garbage
input → save with derived name → editor reload round-trip → validation
surfacing in the save flow → sidebar fit at 640px). Screenshots
inspected: pending-path preview with the new sidebar, the New Map
dialog, and the sidebar at minimum window height. Guide HTML
tag-balance clean.
