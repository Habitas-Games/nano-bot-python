# v0.0.17 — Explicit Selection & Persistence Analysis

**Status:** Complete
**Depends on:** [../v0.0.16/changelog.md](../v0.0.16/changelog.md)

---

## 1. Trigger

"for the simmulation I would rather not have autorun it picks always
the first map, and strategies. Also I do not want fixed folder, for the
maps and strategies a file picker and save the last folder picked as
default 2 values one for strategies and one for map, also save the last
strategies and maps used if the app is rebooted. For the tournament,
change to select files adding one at a time the competitors or several
at the same time during file selection."

Three connected complaints about the same design flaw: the app kept
deciding things by *folder position* instead of user choice —

1. **Run Match auto-ran** a match with the alphabetically-first map and
   strategies before the user chose anything (v0.0.15 improved *which*
   defaults, but the real fix is not defaulting at all).
2. **Pickers were confined to `maps/` and `strategies/`** — a fixed
   folder listing, not a file picker. Strategy/map files couldn't live
   anywhere else, and the app forgot everything on restart.
3. **The tournament globbed everything in `strategies/`** — the field
   was whatever the folder happened to contain.

## 2. Design

- **`nanobot/core/user_prefs.py`** — a tiny JSON prefs file
  (`.nanobot_prefs.json` in the project root, gitignored) with exactly
  the four remembered things: `last_map_dir` and `last_strategy_dir`
  (the two folder defaults the user asked for), `last_map` and
  `last_strategies` (restored on reboot). Failure-tolerant in every
  direction: missing/corrupt/wrong-shape/unwritable degrades to
  defaults, and stored paths are filtered by existence at read time so
  a deleted file degrades to "unset", never to a glob fallback.
- **`FileBrowserModal`** (widgets) — a real navigable browser: shows
  the current folder's subdirectories plus files matching an extension
  filter, ".." to go up, wheel scrolling, path header. In multi-select
  mode files toggle checkmarks and an "Add (n)" button confirms the
  set — "one at a time or several at the same time" are the same
  interaction. `FilePickerModal` (fixed list) stays for the Replays…
  menu, where a curated recency list is the right shape.
- **Match window opens empty.** Run Match on the menu just opens the
  workspace (the menu's whole background-simulation apparatus —
  thread, spinner, result plumbing — deleted). Selectors restore the
  last session's choices where the files still exist; otherwise they
  read "(pick a map)" / "(pick strategy)" and the button reads "Run
  Match" (flipping to "Restart" once something is on screen). Running
  with unset slots produces an instruction, not an error tone. The
  glob-first-file fallback in `_init_selection_from_log` is gone for
  the same reason the menu autorun is.
- **Tournament**: a competitors list with "Add Competitors…"
  (multi-select browser), per-row remove buttons, a match-count
  preview, and Start gated on ≥2. Maps stay "every shipped map" — the
  user's request was about competitors, and the shipped pool is two
  curated maps.

## 3. Defect found during verification

The interaction harness caught a real one before it shipped: the
tournament's not-started draw branch returned early and skipped
`browser.draw()` — the Add Competitors dialog opened (state said so)
but never rendered, in exactly the phase it exists for. Restructured so
the browser always draws last.

## 4. Verified

36 scripted end-to-end checks (real pygame events through real
handlers): empty open, no-selection message, browser navigation
('..'/into folders), extension filtering, single picks, prefs
persistence at pick- and run-time, a full real match, a simulated
reboot restoring selections, stale-prefs degradation, tournament
multi-add (2 at once + 1 singly), row removal, and a real 2-competitor
tournament to completion with exactly the chosen field on the
leaderboard. Screenshots inspected for the empty workspace, the
browser, the tournament setup list, and the post-run state. 330 unit
tests (+9 for user_prefs).
