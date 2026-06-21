# v0.0.4 — Playback Asset Parity Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Port `map_renderer.gd`'s rendering logic into `playback_viewer.py`
directly — same texture set, same flip-direction mapping for streams,
same tint formula for owned habitas points — rather than designing new
visuals, since the goal is parity with assets that already exist and are
already correct elsewhere in the project.

## Order

1. Add texture loading (`_load`, mirroring `map_canvas_renderer.py`'s
   helper) and a `_scaled` cache to `PlaybackViewer.__init__`.
2. Replace `_draw_map`'s flat `DENSITY_COLOR` rects with the real tile
   textures, falling back to the flat color only if a texture file is
   genuinely missing.
3. Replace the procedural-only stream arrow with the real stream texture
   (flipped per direction, matching the map editor and Godot exactly)
   plus the existing crisp procedural arrow drawn on top — both layers,
   not one replacing the other, matching `map_renderer.gd`'s own
   two-layer approach.
4. Replace `_draw_habitas`'s plain circle with the real neutral/owned
   textures, adding a `_owned_tinted` cache keyed by `(size, tint)` since
   the tint result only depends on the player's color and the
   destination size, not on which specific habitas point it's drawn for.
5. Replace `_draw_azn`'s plain circle with the real `azn_node.png`
   texture.
6. Verify every texture path loads (direct load test for all 4 tile
   densities, both stream orientations, both habitas variants, the AZN
   marker), then verify visually: render the bundled replay's early
   frame (all-neutral habitas) and a later frame located by scanning for
   the first `owner >= 0` habitas point, to see both the neutral and the
   tinted-owned texture actually on screen, not just assume the tint math
   is right.
7. Full regression sweep (pytest, `tests/check_editor.py`, a real
   headless CLI match) to confirm nothing outside `playback_viewer.py`
   was touched.

## Explicit non-goals for this version

- No change to bot rendering — already correct (real sprite + ring),
  not part of the gap this version addresses.
- No change to the map editor — it already used these textures.
- Map/strategy selection UI, restoring match stats, and the
  `index.html`/participant-guide question raised in the same
  conversation are separate, larger pieces of work — scoped to their own
  versions rather than folded in here.
