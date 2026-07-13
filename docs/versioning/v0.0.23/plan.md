# v0.0.23 — Folder Dialog Freeze Fix Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Order

1. Replace in-process `_ask_directory()` with
   `_launch_directory_dialog(initial)` — `subprocess.Popen` of a
   7-line tk script printing the chosen path; returns the Popen (or
   None if launch failed). Module-level for test stubbing.
2. FileBrowserModal state machine: `_dialog_proc` field;
   `_open_os_dialog` launches (guarded to one at a time);
   `_poll_dialog` (called first in `draw()`) reads the result on exit
   and navigates / falls back to typed path on nonzero exit / no-ops
   on cancel; `_cancel_dialog` kills the child. Wire Esc (while
   pending) and both `open()`/`close()` to `_cancel_dialog`.
3. Draw a "waiting for the system dialog" panel while pending and
   clear the interactive rects so nothing underneath is clickable.
4. Verification: 9-check script (stubbed pending/complete/cancel/
   Esc/close + a real display-less subprocess exercising the
   fallback); full pytest.
5. Docs; commit + push.

## Explicit non-goals

- Embedding a native file dialog inside the pygame window — not
  possible without a full in-engine file widget; the OS dialog in a
  subprocess is the right tool.
- Threading instead of a subprocess — a tk thread still shares the
  process's GIL/loop and the SDL/tk conflict remains; a process
  boundary is what actually isolates them.
