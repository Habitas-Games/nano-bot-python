# v0.0.23 Changelog

**Version:** 0.0.23
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Fixes the whole-app freeze when opening the folder picker (reported
with a screenshot). The v0.0.22 dialog ran tkinter in-process, which
blocked pygame's loop and — because SDL and tk can't share a main
thread on Linux — could wedge the app entirely. The dialog now runs in
a **separate process** while the app keeps rendering and stays
cancellable.

## Fixed

- **Folder… no longer freezes the app.** The OS folder dialog runs in
  a subprocess with its own event loop; the browser polls it each
  frame and shows a "Choose a folder in the system dialog…" state
  while it's open, so the window keeps drawing and responding.
- **Esc abandons a pending dialog** (kills the child process), and
  closing or reopening the browser cleans up any pending dialog — no
  orphan processes. Only one dialog opens at a time.
- Unchanged behavior otherwise: a chosen folder navigates there,
  cancel is a no-op, and a system with no working dialog (tkinter
  missing / no display) still falls back to the click-to-type path
  editor — now driven by the child's exit code.

## Verification

```
$ pytest tests/  -> 362 passed (widget-only change)
9-check interaction script: subprocess launch; app keeps drawing while
  pending; input swallowed while waiting; completion navigates; cancel
  no-op; Esc kills the child; browser-close kills the child; and a
  REAL subprocess with DISPLAY/WAYLAND_DISPLAY stripped, exercising
  the genuine failure -> typed-path fallback (not mocked).
```
