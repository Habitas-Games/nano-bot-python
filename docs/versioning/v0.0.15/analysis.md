# v0.0.15 — UX & QA Review Analysis

**Status:** Complete
**Depends on:** [../v0.0.14/changelog.md](../v0.0.14/changelog.md)

---

## 1. Trigger

"help me do ux and qa review and fix any issue that appears. Improve
wherever possible on the usability specially."

## 2. Method

Same discipline as every prior version: nothing was called a bug from
code-reading alone. A headless harness rendered every screen in its
suspect states (dummy SDL driver, real draw calls, saved screenshots)
and drove real pygame events through the real handlers; each finding
below was confirmed either by a screenshot or by a scripted
interaction check before being fixed, and re-confirmed after.

## 3. Confirmed defects (all fixed)

1. **Match-status text drawn over the Replays…/Seed buttons** (playback
   viewer). The status message and the "Simulating…" spinner were
   anchored at `btn_restart.rect.right` — correct until v0.0.14 added
   two more buttons to that row. Screenshot showed the result text and
   both button labels overprinted and unreadable. This fired after
   *every* restart — the single most common interaction on the screen.
2. **Events ticker collides with the Bot Inspector** at small window
   heights (screenshot at 1000×620: rows drawn under the inspector
   panel). Compounded by the window being freely resizable to any size.
3. **Main menu Quit button off-screen** below ~660px window height
   (screenshot at 1024×600: Quit half-clipped; at 1024×560 it would be
   gone entirely, taking the only in-app quit path with it).
4. **Tournament leaderboard columns ragged.** The table was built with
   f-string padding (`{name:<28}`), which only aligns in a monospace
   font — `draw_text` renders a proportional SysFont. Screenshot shows
   the W/L/D columns wandering per row.
5. **Tournament not re-runnable.** `_start` guarded on `self.started`,
   which was never reset — after one run, Start stayed dead until app
   restart.
6. **Editor Undo button never enables from editing.** All eight tools
   push undo snapshots, but none called `sidebar.set_undo_enabled` —
   only Load/Clear/Undo itself did. Paint one cell after loading and
   the Undo button sits greyed out, telling the user there's nothing
   to undo when there is. (Caught from a QA screenshot of an unrelated
   check; confirmed by driving a real paint event.)
7. **Viewer tooltips silently never rendered.** `Button.tooltip` was
   only drawn by the map editor sidebar's own code; the two tooltips
   added to the viewer in v0.0.14 (Replays…, seed lock) were dead text.
8. **Editor save dialog forgets the filename.** Loading
   `bone_maze.json` and hitting Save prefilled `my_map.json` — saving
   back to the file you're editing meant retyping its name every time.
9. **Silent data loss on Load.** The editor's Load picker replaced the
   document with no unsaved-changes warning of any kind.

## 4. Usability gaps (improved)

- **Zoom drifted to the map origin.** Both canvases zoomed about the
  top-left corner, so wheel-zooming into a fight slid the fight out of
  view. Both now anchor at the cursor (and the viewer's steps are
  multiplicative — the old flat +0.1 was glacial at 6× and coarse at
  0.5×).
- **The viewer opened cropped and paused.** Fixed 1.5× zoom at scroll
  (0,0) cropped every map bigger than ~48 cells, starting with the far
  player's spawn off-screen; and every path into a replay (first match,
  Restart, Replays…) landed paused at turn 0. Now: fit-to-window,
  centered, auto-playing.
- **Pan could lose the map entirely** — no scroll clamping in the
  viewer (the editor's Pan tool had it; middle-drag was about to
  inherit the gap). Both canvases now clamp; `F` re-fits the viewer.
- **Keyboard was undiscoverable and barely usable.** Space/←/→ existed
  but nothing on screen said so, and pygame sends one KEYDOWN per
  press, so stepping 100 turns meant 100 key presses. Now: key repeat
  (main.py), Home/End, F, and a hint line in the top bar's dead space.
- **Watching a full match took ~3 minutes minimum.** Speed capped at
  4×; now 16× (~12s to skim 1500 turns).
- **Seeds weren't in replays.** The seed display/lock only knew seeds
  for matches the viewer itself launched; opening any saved replay
  showed "Seed —" forever. Replays now store their seed (backwards
  compatible: old files load as None and keep showing "—" rather than
  lying with a default).
- **First impression was a stomp.** Run Match picked the first two
  strategies alphabetically: example_combat vs example_container —
  a 287-turn 70-0 wipeout (verified from the replay it left behind).
  It now prefers example_explorer vs example_defense when present —
  verified 200-170 over the full 1500 turns in the end-to-end check.
- **Tournament was a bare progress bar** while running (nothing to
  watch), printed the results path with `../../..` noise, and treated
  all ranks alike. Now: live standings during the run, podium colors
  on the top 3 (closes TRN-05), normalized path, "Run Again".
- **Editor round-trips**: middle-drag pan from any tool (switching to
  the Pan tool and back was the most repetitive edit-session loop),
  Ctrl+Z/Ctrl+S, filename + unsaved-changes marker in the top bar.
- **Replay picker rows were bare filenames**; now each shows its age
  ("3 min ago") — the modal also sizes to fit its labels.
- **Window could be resized into any of the broken layouts above**;
  resizes now clamp to 1024×640, the smallest size every screen was
  verified at.

## 5. Non-goals

- Touching engine rules, balance, or strategy code — this is a UX/QA
  pass; the simulation behaves identically (seed field aside, which is
  additive to the replay format).
- An editor hazard-authoring tool (MAP-08) — still the known gap.
- Unit tests for pygame rendering — per project convention, UI changes
  are verified by scripted integration checks and screenshots instead;
  the two new unit tests cover the core `MatchLog.seed` change.
