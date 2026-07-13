# v0.0.22 — Browser Folder Selection Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Order

1. **`_ask_directory(initial)`** module function in widgets.py:
   tkinter `askdirectory` wrapped so the three outcomes are explicit
   (path / "" cancel / None unavailable); monkeypatchable for tests.
2. **FileBrowserModal**: `_navigate_to(path)` helper (abspath +
   expanduser + isdir gate, resets scroll/filter); "Folder…" footer
   button wired to the dialog with typed-path fallback when it
   returns None; path line becomes a click target with hover state;
   `_editing_path`/`_path_buffer` keyboard mode (Enter navigates,
   stays open on bad paths; Esc cancels; isolated from the
   type-to-filter); footer scroll-count text shifted to clear the
   button; hint line now says "click path to edit | type to filter".
3. **Verification**: 13-check script with the dialog monkeypatched
   (navigate / cancel / unavailable), typed navigation, `~`
   expansion, filter isolation; screenshot; full pytest.
4. **Docs**: guide quickstart mention; this folder; commit + push.

## Explicit non-goals

- Clipboard paste into the path field — pygame's clipboard support
  (pygame.scrap) is unreliable cross-platform; typing plus the OS
  dialog covers the need.
- Bookmarks/recent-folders list — the per-type last-folder memory
  (v0.0.17) already covers the common case.
