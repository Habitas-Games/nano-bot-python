# v0.0.15 — UX & QA Review Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Audit first, fix second, verify third — with the audit and the
verification using the same headless harness so every "fixed" claim is
the same screenshot/interaction that demonstrated the defect, re-run
green. Shared plumbing lands before the screens that use it.

## Order

1. **App shell** (`main.py`): minimum window size (1024×640 — the
   smallest size at which every screen is verified sane) enforced on
   VIDEORESIZE; `pygame.key.set_repeat` so held keys repeat everywhere.
2. **Core** (`match_log.py`, `simulation_core.py`): `MatchLog.seed`,
   written by the sim, serialized only when present, loaded as `None`
   when absent (old replays must not pretend reproducibility). +2 unit
   tests (round-trip, missing-field default).
3. **Widgets** (`widgets.py`): `draw_hover_tooltips` shared helper
   (sidebar's private implementation promoted; sidebar now calls it);
   `FilePickerModal.open(..., labels=)` with width-to-fit.
4. **Playback viewer**: status strip; ticker clipping above the
   inspector; cursor-anchored multiplicative wheel zoom; scroll clamp;
   `_fit_view` on load + `F`; auto-play on every load path
   (`_set_playing` icon-safe helper); SPEEDS to 16×; Home/End; hint
   line; seed from log; replay picker age labels.
5. **Main menu**: button stack clamped to the window bottom, subtitle
   anchored to the stack; Run Match prefers the explorer-vs-defense
   matchup when both demo files exist.
6. **Tournament screen**: fixed-pixel-column `_draw_leaderboard`
   (podium colors, used both live and finished), re-runnable Start
   ("Run Again"), normalized results path, enabled-state set in draw.
7. **Map editor**: `current_filename` + `_saved_history_pos` (via a new
   `MapHistory.position` property) → save-name prefill, top-bar
   file/unsaved indicator, confirm-discard modal guarding Load;
   Ctrl+Z/Ctrl+S; cursor-anchored wheel zoom + `_clamp_scroll`;
   middle-drag pan from any tool (defensive `getattr` for synthetic
   events); per-frame `set_undo_enabled` sync in `draw()` (kills the
   whole missed-callback bug class); action-button tooltips.
8. **Verification**: harness re-run (19 behavioral checks + screenshots
   of every fixed state), end-to-end app flow (menu → real simulated
   match → viewer auto-playing with the new defaults; editor paint →
   Undo enabled), full pytest (321), `tests/check_editor.py`.
9. **Docs**: requirements rows (TRN-05 ✅, VIS-04/UX-04 wording),
   participant guide quickstart, README, this folder.

## Explicit non-goals

- Engine/balance changes; editor hazard tool (MAP-08); SCO-03.
