# v0.0.3 — UX Follow-up Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Treat the map editor and the playback viewer as one consistent surface —
every issue raised was either present in both or, once found in one, was
explicitly checked for in the other rather than assumed absent. Fix in
dependency order (shared building blocks first, screen-specific wiring
second) so each piece can be verified in isolation before the next one
depends on it.

## Order

1. **Icon set** (`nanobot/ui/icons.py`) — built and visually verified
   first (rendered to a PNG, inspected directly) since both screens'
   button conversions depend on it existing and looking right.
2. **Map editor sidebar** — convert Elements/Tools rows to icon-button
   grids; refactor header-label positions to be recorded during
   `_build()` rather than recomputed by hand in `draw()` (the project
   already has a known anti-pattern here from earlier sessions); fix the
   resize-staleness bug this surfaced.
3. **Map editor top bar + Menu button** — active-tool/tile preview,
   back-to-menu control, draw-order fix for the button-hidden-under-
   sidebar bug this surfaced.
4. **Map editor grid color** — SRCALPHA overlay technique, confirmed via
   pixel inspection before trusting it.
5. **`main.py` ESCAPE handling** — defer to a screen's own modal-cancel
   logic before falling back to "go to menu."
6. **Playback viewer** — same three treatments applied second, once the
   icon set and the SRCALPHA grid technique were already proven correct
   in the editor: icon buttons for play/pause/step/speed, back-to-menu
   button, SRCALPHA grid overlay. Reused the established techniques
   rather than re-deriving them.
7. Full regression sweep (pytest, `tests/check_editor.py`, a real
   headless CLI match) plus fresh screenshots of both screens.

## Verification

- Every visual change checked against an actual rendered screenshot
  (`SDL_VIDEODRIVER=dummy` + `pygame.image.save`), not just "the drawing
  code looks right" — this caught the hidden-menu-button bug, which had
  perfectly reasonable-looking code and only failed once actually
  rendered and viewed.
- The alpha-blending fix specifically verified at the pixel level
  (`surface.get_at()`) before and after, since it's the kind of
  assumption ("alpha just works") that's easy to get wrong silently.
- Full existing test suite (280 tests) re-run after every file change,
  not just at the end, to attribute any failure immediately.
- `tests/check_editor.py` re-run after every editor-affecting change.
- A real headless CLI match re-run at the end to confirm none of this
  UX work touched simulation behavior (it shouldn't have — no
  `nanobot/core/` or `nanobot/tournament/` files were touched this
  version).

## Explicit non-goals for this version

- No simulation, scoring, or JSON format changes — this version is UI
  only.
- No new automated tests — the changes are pygame rendering/layout, which
  the project already treats as integration/screenshot-verified rather
  than unit-tested (v0.0.2 plan.md's non-goals named this explicitly as
  future scope; still not taken up here, since the verification method
  already in place caught everything found this round).
- No redesign of the HUD or inspector panel — reviewed and found
  already legible; changing either without a specific issue would be
  scope creep beyond what was asked.
