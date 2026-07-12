# v0.0.17 — Explicit Selection & Persistence Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Plumbing first (prefs, browser widget), then the three screens that
use it, then a single end-to-end interaction harness that walks the
whole user story: fresh start → empty window → browse → pick → run →
"reboot" → restored.

## Order

1. **`nanobot/core/user_prefs.py`** + 9 unit tests (round-trip, merge,
   missing/corrupt/wrong-shape tolerance, existence filtering for
   file/files/dir) + `.nanobot_prefs.json` gitignored.
2. **`FileBrowserModal`** in widgets.py: directory navigation with
   ".." row, hidden/`__pycache__` skipping, extension filter, wheel
   scroll with range indicator, single-select (click = choose) and
   multi-select (checkboxes + "Add (n)" + Enter) modes, path header
   with middle-truncation, click-outside/Esc to cancel.
3. **Playback viewer**: `replay_path=None` opens the workspace empty;
   selection state restored via `user_prefs.existing_file(s)`; glob
   fallbacks removed (log-seeded selection only overwrites slots whose
   files exist); pickers switched to the browser (per-type start dirs,
   dirs persisted on pick); selections persisted on Run; "Run Match" ↔
   "Restart" label; instructive empty-state canvas text; slider hidden
   while empty; invalid-map error surfaced from the worker.
4. **Main menu**: Run Match = open the window; the menu's background
   simulation apparatus (thread/spinner/message/update) deleted.
   main.py: `_open_playback(None)`, ESC-check generalized to any
   open `picker`/`browser` attribute.
5. **Tournament screen**: competitors list (add via multi-select
   browser, per-row ×, count preview, Start gated on ≥2, field kept
   across Run Again); browser drawn in every state (the early-return
   skip was a caught defect); runner receives the chosen list instead
   of a glob.
6. **Verification**: 330 unit tests; 36-check interaction harness +
   screenshot inspection (empty, browser, tournament setup, post-run).
7. **Docs**: VIS-07 and TRN-01 (Revision 4) rewritten, README/guide/
   index.html flow text, this folder.

## Explicit non-goals

- Tournament map selection stays "every shipped map" — the request
  was competitor selection; revisit if map count grows.
- Replays… keeps the fixed recency list (curated, newest-first) — it
  is not a folder-position default, it's a history view.
- No prefs UI — the file is a cache of last use, not settings.
