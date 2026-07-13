# v0.0.22 Changelog

**Version:** 0.0.22
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

The file browser gets real folder navigation: a **Folder…** button
that opens the operating system's folder picker, and a **click-to-type
path line** — jumping anywhere is now one action instead of a
dozen ".." clicks. Applies everywhere the browser is used: the match
window's map/strategy pickers and the tournament's competitors/maps.

## Added

- **Folder… button** (browser footer): opens the OS folder dialog
  (tkinter, verified present). Cancel changes nothing; on systems
  with no dialog available the button falls back to the typed-path
  editor instead of failing silently.
- **Editable path line**: click the current-path display, type or
  correct a path (`~` expands to home), Enter navigates, Esc cancels.
  A nonexistent path keeps the editor open to fix rather than
  discarding the input. Path typing is fully isolated from the
  type-to-filter. Hint line updated: "click path to edit | type to
  filter".

## Verification

```
$ pytest tests/  -> 362 passed (widget-only change)
13-check interaction script: dialog navigate/cancel/unavailable
  (monkeypatched), fallback into path editing, click-to-edit, typed
  navigation with listing refresh, ~ expansion, bad-path retention,
  filter isolation, Esc handling. Screenshot inspected. tkinter
  probed available (Tk 8.6) for real desktop use.
```
