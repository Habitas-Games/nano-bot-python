# v0.0.23 — Folder Dialog Freeze Fix Analysis

**Status:** Complete
**Depends on:** [../v0.0.22/changelog.md](../v0.0.22/changelog.md)

---

## 1. Trigger

"I was trying to select a folder and the whole program froze" — with a
screenshot showing the tk folder dialog open on top of a frozen app.

## 2. Root cause

v0.0.22 called `tkinter.filedialog.askdirectory()` **in-process**,
directly inside the pygame frame. That does two bad things at once:

- It **blocks** — the call doesn't return until the user finishes the
  dialog, so pygame stops pumping events and drawing; the whole window
  is frozen for as long as the dialog is up.
- Worse, on Linux **tkinter's event loop and SDL's can't coexist on
  the same main thread** — the two windowing stacks fight, and the app
  can wedge outright rather than merely pausing (which is what the
  screenshot shows).

An in-process dialog was the wrong architecture, not a tunable.

## 3. Fix: dialog in a subprocess, polled each frame

The tk dialog now runs in a **separate Python process**
(`subprocess.Popen([python, "-c", <7-line tk script>, initial_dir])`),
so it has its own event loop and never touches SDL's. The browser:

- launches it on the Folder… click and stores the `Popen`;
- while it's alive, shows a "Choose a folder in the system dialog…"
  state and **keeps rendering and responding** — no freeze;
- polls it every `draw()`; on exit, reads one line of stdout (the
  chosen path, empty = cancel) and navigates, or — if the child
  exited nonzero (tkinter unavailable) — drops into the typed-path
  fallback;
- **Esc abandons the wait** (kills the child), and closing the browser
  or reopening it also kills any pending dialog, so no orphan
  processes.

Only one dialog can be open at a time (guard on `_dialog_proc`).

## 4. Why this is verifiable despite being a GUI/OS feature

The launch is behind a module-level `_launch_directory_dialog()` seam,
so tests stub it with a fake Popen and drive the full state machine —
pending (app still draws, input swallowed), completion (navigates),
cancel (no-op), Esc (kills child), browser-close (kills child). And
one check runs the **real** subprocess with `DISPLAY`/`WAYLAND_DISPLAY`
stripped, so the child genuinely fails to open a dialog and the
typed-path fallback is exercised for real, not mocked.

## 5. Verified

9-check interaction script (7 stubbed states + 1 real-subprocess
failure-to-fallback + responsiveness-while-pending), all pass; 362
unit tests unchanged-green (widget-only). The one thing no headless
test can show — the native dialog visibly appearing while the app
stays interactive behind it — is now architecturally guaranteed by
the process boundary rather than hoped for.
