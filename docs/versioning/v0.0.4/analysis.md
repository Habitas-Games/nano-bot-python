# v0.0.4 — Playback Asset Parity Analysis

**Status:** Complete
**Depends on:** [../v0.0.3/changelog.md](../v0.0.3/changelog.md)

---

## 1. Trigger

The user asked what happened to the original Godot project's art assets
and whether they could be used in this port. Auditing both projects'
`assets/` directories against what each codebase actually loads (not just
what files exist on disk) surfaced a real, specific gap, confirmed by the
user directly: **"the run match does not use the assets."**

## 2. What the audit found

Cross-referencing every asset file against `grep` hits in both
codebases:

| Asset | Used by Godot | Used by Python map editor | Used by Python playback (before this version) |
|---|---|---|---|
| `tiles/tile_{low,medium,high,bone}.png` | Yes (`map_renderer.gd`) | Yes (`map_canvas_renderer.py`) | **No — flat `DENSITY_COLOR` rects** |
| `tiles/tile_stream_{h,v}.png` | Yes | Yes | **No — procedural lines only** |
| `markers/habitas_neutral.png` | Yes | Yes | **No — plain circle** |
| `markers/habitas_owned.png` | Yes, multiply-tinted per owner | N/A (editor has no ownership concept) | **No — plain circle, wrong color model entirely** |
| `markers/azn_node.png` | Yes | Yes | **No — plain circle** |
| `bots/bot_*.png` | Yes | N/A | Yes (already correct) |

The map editor was never the problem — it has used the real textures
since the original port. The playback viewer — what actually renders
when running a match or replay, the screen most people spend the most
time looking at — was built with placeholder flat-color/procedural
shapes for everything except the bot sprites, despite the real art
sitting unused in the same `assets/` folder it already imports from for
bots.

This corrects something stated incorrectly in conversation just before
this version: `habitas_owned.png` was claimed to be unused in Godot too.
Re-checking `map_renderer.gd` directly showed that's wrong — it's
preloaded and drawn with a per-player multiply-tint
(`base_col.lerp(Color.WHITE, OWNED_BLEND)`, `OWNED_BLEND = 0.30`). The
Python playback viewer was the only place this texture went unused.

## 3. Why a multiply-tint, and why it's safe here unlike the bot sprites

v0.0.1/v0.0.2's UX work already tried and rejected a multiply-tint for
*bot* sprites — `BLEND_RGBA_MULT` against the sprites' own multi-color
art muddied the colors and was barely legible against red terrain, so
team identity was moved to a colored ring drawn around the sprite
instead. `habitas_owned.png` is a different kind of asset: sampling its
center pixel directly (`(254, 254, 253, 255)`) confirms it's a
near-white base texture, purpose-built for multiply-tinting — multiplying
white by any color reproduces that color exactly, which is exactly what
Godot's own renderer relies on. Confirmed by rendering both the neutral
marker and a tinted owned marker (forcing a frame where a habitas point
actually has an owner, since the bundled replay's early frames are all
neutral) and visually inspecting the result before trusting the
approach.

## 4. Scope boundary

This version only changes *rendering* in `playback_viewer.py` — texture
loading, scaling, flipping, and tinting, mirroring
`map_canvas_renderer.py`'s existing patterns and `map_renderer.gd`'s
exact logic (flip directions, tint blend factor). No simulation logic,
scoring, or JSON formats changed; `_draw_bots`' existing ring-based team
coloring is untouched since it was already correct and already uses its
asset (the bot sprite).
