# v0.0.22 — Browser Folder Selection Analysis

**Status:** Complete
**Depends on:** [../v0.0.21/changelog.md](../v0.0.21/changelog.md)

---

## 1. Trigger

"on the file selector windows I am missing an easy way to change the
folder. Maybe a button to select the folder with the os folder
selector. NO way to easy set the folder or select it."

Fair: the FileBrowserModal could only walk one level at a time
(".." and folder rows). Reaching a distant folder — another project,
a downloads directory — meant a dozen clicks with no way to jump.

## 2. Design: two affordances, one shared widget

1. **"Folder…" button** (footer, all browser uses — match window's
   three pickers, tournament's competitors and maps): opens the OS
   folder picker via tkinter's `askdirectory` (verified available on
   this machine, Tk 8.6). The call lives in a module-level
   `_ask_directory()` so tests can monkeypatch it and so the failure
   mode is explicit: it returns the chosen path, `""` on cancel, or
   `None` when no dialog exists (headless, tkinter not installed) —
   in which case the button drops into typed-path mode instead of
   dying silently. The tk root is created, withdrawn, and destroyed
   per call; the pygame loop blocking while the (modal anyway) dialog
   is open is acceptable and standard.
2. **Click-to-type path**: the path line is now a click target —
   click, type or fix a path (`~` expands), Enter navigates,
   Esc cancels. A bad path keeps edit mode open to correct rather
   than throwing the input away. This is both the fallback for
   systems without tkinter and the fast path for people who know
   where they're going. While editing, printable keys go to the path
   buffer, never the type-to-filter (verified).

The scroll-count footer text moved right to clear the new button.

## 3. Verified

13-check interaction script: OS-dialog navigation (monkeypatched),
cancel = no-op, unavailable-dialog fallback into path editing,
click-to-edit, typed navigation with listing refresh, `~` expansion,
bad-path retention, filter isolation, Esc handling; screenshot
inspected (button + "click path to edit | type to filter" hint).
tkinter probed as actually present for desktop use. 362 unit tests
unchanged-green (widget-only change, no engine surface).
