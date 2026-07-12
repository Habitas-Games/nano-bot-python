# v0.0.20 — Review Findings Fix-All Analysis

**Status:** Complete
**Depends on:** [../v0.0.19/changelog.md](../v0.0.19/changelog.md)

---

## 1. Trigger

A full UX/QA review of the v0.0.19 app (probe scripts + screenshots,
9 findings + a roadmap list), followed by "fix all".

## 2. The two "app lies to you" defects

1. **Strategy failures were invisible in the GUI.** Measured: a
   crashing strategy produced 1,500 console warnings and **zero**
   on-screen signals — its bots simply froze. For a programming
   competition this was the worst possible debugging experience: a
   participant's first buggy strategy looked like the game ignoring
   them. Fixed at the source: the engine now emits `strategy_error`
   (exception type + message) and `strategy_timeout` (measured ms)
   events into the replay, and the viewer's Events ticker narrates
   them in warning color. Consecutive identical lines collapse to one
   timeline entry (a strategy crashing every one of 1500 turns is one
   story beat, not 1500).
2. **Replays whose map was deleted rendered silently wrong** — bots
   floating on a blank 40×40 grid with no bone or streams, while the
   selector showed a *different* map name than the HUD. Now: a red
   banner ("Map 'X' not found in maps/ — showing blank terrain
   (bots/objectives are real, walls and streams are not)") plus a
   "(file missing!)" marker on the HUD's map line.

While probing this, a third latent defect surfaced: every UI module
built its maps/strategies/replays paths with unnormalized `../..`
segments — those paths leak into user_prefs and equality checks, where
`a/b/../c` and `a/c` silently count as different files. All module dir
constants are now normpathed.

## 3. The rest of the findings

- **Editor status bar** overlapped the filename indicator at minimum
  width (screenshot-confirmed) → status text now truncates with an
  ellipsis to the space available before the filename.
- **Tournament competitor list had no ceiling** → windows to 8 rows
  with wheel scrolling and a "showing a–b of n" line.
- **Replays… capped at newest-14** with 88 replays on disk → lists
  everything, scrollable (shared scrollbar), and each row gets an [x]
  that deletes the file (replays are regenerable match logs, not user
  documents; the modal stays open for batch cleanup).
- **File browser** was wheel-only and unfilterable → proportional
  scrollbar + type-to-filter (substring on names; first Esc clears
  the filter, second closes).
- **No Help in the app** → a Guide button on the main menu opens
  `docs/participant_guide.html` in the system browser; the 5-button
  stack still clears the 640px minimum (bottom = 624).
- **Tournament maps weren't selectable** → "Maps…" multi-select
  (default: all shipped maps), match-count preview updates, and the
  in-play map names are listed on the setup screen.
- **Roadmap niceties from the review, all in**: editor **redo**
  (Ctrl+Y / Ctrl+Shift+Z + sidebar button — the history stack
  snapshots pre-mutation states, so undo() captures the post-edit
  state into a redo stack at the only moment it exists), ticker
  **click-to-jump** (rows are clickable, with hover highlight), and a
  **follow camera** (C follows the selected bot; manual pan or F
  releases it).

## 4. Left open, deliberately

**SCO-03** (per-map bonus objectives) is a game-design decision, not a
fix — implementing or dropping it changes scoring rules, which "fix
all" doesn't license. It stays ⬜ pending the user's call, and is now
the only open M7 item.

## 5. Verified

352 unit tests (+4: strategy failure events ×3, redo ×4 in
map_history, minus none); 31-check interaction harness covering every
finding end-to-end (real events; includes deleting a real replay file
via the picker [x] and running the crash/ghost scenarios through the
actual sim); screenshots inspected for the crash ticker, the
missing-map banner, the scrolled tournament list, the maps selection,
and the truncated editor status bar.
