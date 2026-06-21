# v0.0.6 — Marketing Site & Participant Guide Port Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Keep the original HTML/CSS structure, layout, and visual design entirely
intact — same sections, same class names, same styling — and change only
the text content and a handful of section-specific blocks (the
Godot-technology section, the Contribute section's links) that are
inherently about the Godot version specifically. Verify every restated
technical fact against the actual Python code before writing it, rather
than mechanically swapping "GDScript" for "Python" in place.

## Order

1. Read both Godot HTML files in full (`index.html`, 623 lines;
   `participant_guide.html`, 776 lines) to know exactly what needs
   adapting.
2. Cross-check every factual claim against the live `nano-bot-python`
   code: `data/bot_types.json`, `nanobot/api/*.py`,
   `nanobot/core/map_data.py`, `nanobot/core/simulation_core.py`, and
   both example strategy files — see analysis.md §4 for the full list of
   what was checked and confirmed.
3. Resolve the one piece of information not derivable from the
   code — what to do about the hardcoded GitHub repo URL — by asking
   directly rather than guessing (analysis.md §6).
4. Copy the four real-but-previously-uncopied assets
   (`cover.png`, `deuna_qr.png`, `Tier 1 — Bot Sprites.png`,
   `markers/injection_zone.png`) into `nano-bot-python/assets/`.
5. Write `index.html` and `docs/participant_guide.html`, reusing the
   original CSS verbatim and only changing the content blocks identified
   in step 2.
6. Verify structurally: HTML tag balance (no unclosed/mismatched tags),
   every `src`/`href` in both files resolves to a real local file (script
   checked, fragment-only hrefs like `#api` correctly excluded).
7. Attempt a rendered visual check; document the result honestly either
   way rather than claim a screenshot that wasn't actually taken.

## Verification

- Tag-balance check via `html.parser.HTMLParser` for both files.
- Path-resolution check: every `src="..."` and local `href="..."` in
  both files resolved against the file's own directory and confirmed to
  exist on disk.
- Attempted `firefox --headless --screenshot` to get an actual rendered
  image; it failed in this sandboxed environment (snap-wrapped Firefox
  profile lock, then a timeout with a fresh profile). No other headless
  browser or `wkhtmltoimage`-equivalent was available. This is recorded
  here rather than glossed over — the structural and content checks
  above are real, but nobody has visually confirmed the rendered page
  layout looks right in an actual browser yet.

## Explicit non-goals for this version

- No changes to `nano-bot-python`'s actual application code — this
  version is HTML/asset content only.
- No CSS redesign — the original's visual design is kept as-is, per the
  user's explicit "same content, Python-ized" scope choice.
- Not fixing the missing `assets/menu/` background+logo or `assets/fx/`
  event animations flagged earlier in this conversation — still tracked
  as open follow-ups, not part of this version's HTML-port scope.
