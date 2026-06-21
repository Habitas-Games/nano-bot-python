# v0.0.4 Changelog

**Version:** 0.0.4
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

The playback viewer (what renders after "Run Match" or opening a replay)
was drawing flat colors and procedural shapes for terrain, streams,
habitas points, and AZN nodes instead of the real art assets already
sitting in `assets/` and already used correctly by the map editor and
the Godot original. This version wires the real textures in, matching
`map_renderer.gd` exactly (same flip directions, same owned-habitas tint
formula). No simulation logic, scoring, or JSON formats changed.

## Changed

- **`nanobot/ui/playback/playback_viewer.py`**:
  - Added texture loading for `tiles/tile_{low,medium,high,bone}.png`,
    `tiles/tile_stream_{h,v}.png`, `markers/habitas_neutral.png`,
    `markers/habitas_owned.png`, `markers/azn_node.png`, plus a
    `_scaled()` cache (mirroring `map_canvas_renderer.py`'s pattern).
  - `_draw_map` now blits the real density texture per cell instead of a
    flat `DENSITY_COLOR` rect (kept only as a fallback if a texture file
    is genuinely missing).
  - Renamed `_draw_stream_arrow` to `_draw_stream_cell`: now blits the
    real stream texture first (h/v, flipped for `WEST`/`NORTH` exactly
    like the map editor and `map_renderer.gd`), then draws the existing
    crisp procedural arrow on top — both layers, matching Godot's own
    "texture, then a sharp arrow overlay for clarity at small sizes"
    approach, not a replacement of one with the other.
  - `_draw_habitas` now blits `habitas_neutral.png` for an unclaimed
    point or `habitas_owned.png` multiply-tinted toward the owning
    player's color for a claimed one, via a new `_owned_tinted()` helper
    cached by `(size, tint)`. Tint formula matches `map_renderer.gd`'s
    `base_col.lerp(Color.WHITE, OWNED_BLEND)` exactly: `OWNED_BLEND =
    0.30`, i.e. each channel becomes `c + (255 - c) * 0.30`.
  - `_draw_azn` now blits `azn_node.png` instead of a flat circle.

## Fixed

**Corrected a claim made earlier in conversation, not a code bug:**
`habitas_owned.png` was described as unused in both Godot and Python.
Re-checking `map_renderer.gd` directly showed it's actually preloaded
and drawn with a per-player tint — only the Python playback viewer left
it unused. Worth recording since it's the kind of claim that would have
gone stale/wrong in memory otherwise.

No functional bugs found this round — this was a straightforward
asset-wiring port, not a behavior fix.

## Verification

```
$ pytest tests/
280 passed in 0.85s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy0 strategies/example_strategy.py \
    --strategy1 strategies/example_strategy_v2.py --seed 42
HeadlessRunner: match complete in 1500 turns
HeadlessRunner: winner — player 0
```

Plus direct texture-load verification (all 4 tile densities, both
stream orientations, both habitas variants, and the AZN marker
confirmed loaded as real `pygame.Surface` objects, not silently `None`
falling back to flat colors) and visual verification: a screenshot of
an early frame (all habitas neutral) showing the gold neutral marker
correctly inside a HIGH-density terrain patch, and a screenshot of frame
268 — located by scanning the bundled replay for the first frame with
`owner >= 0` on any habitas point, since the early frames are all
neutral — showing the owned marker correctly tinted in the owning
player's red, confirming the multiply-tint actually produces the right
on-screen color rather than just trusting the formula by inspection.

## Known gaps carried forward

- No unit tests for the pygame rendering layer — same gap named in
  v0.0.2 and v0.0.3, still relying on screenshot/integration
  verification rather than a unit suite.
- The main menu's background/logo and the playback viewer's event VFX
  (`assets/menu/`, `assets/fx/`) remain unported — raised in the same
  conversation as a follow-up, not addressed in this version.
