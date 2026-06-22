# v0.0.11 — 1-Indexed Player Labels Analysis

**Status:** Complete
**Depends on:** [../v0.0.10/changelog.md](../v0.0.10/changelog.md)

---

## 1. Trigger

"Change player 0 and player 1 for player 1 and player 2 on the labels."
Display-only: the engine's internal player IDs (dict keys in
`final_scores`/`frame["scores"]`, `winner_id`, `bot["owner"]`, the
`player_id` parameter threaded through `SimulationCore`) stay 0-indexed
— that's the data model every JSON replay file, every test, and the
whole engine already commits to. Only text rendered for a human to read
changes.

## 2. An inconsistency already existed before this request

The playback viewer's map/strategy picker buttons (v0.0.7) already show
**"P1:"/"P2:"** for player slots 0/1 — 1-indexed. Everywhere else that
displays a player identifier — the HUD score rows, the "Winner:" line,
the Bot Inspector's "Owner:" line, the match-summary message on both the
main menu and the playback viewer, and the map editor's zone-tool status
text — showed the raw 0-indexed value ("Player 0", "Player 1"). The same
two players were labeled with two different conventions depending on
which part of the screen you were looking at. This request makes the
whole app consistent with the convention the picker buttons already
used, not introduce a new one.

## 3. What was and wasn't in scope

In scope (rendered UI text, read by a human in the running app):
`playback_viewer.py`'s HUD score rows, winner line, and inspector owner
line; both `playback_viewer.py`'s and `main_menu.py`'s match-summary
message string; the map editor zone tool's status-bar text.

Deliberately left as 0-indexed, since these aren't "labels" in the
sense asked about:
- The CLI tools' (`run_headless.py`/`headless_runner.py`) stdout —
  developer-facing tool output, lowercase "player", a different register
  from the GUI's capitalized "Player" labels.
- `simulation_core.py`'s internal `print()` diagnostics (strategy
  exceptions, timeouts) — engine-side logging, not UI.
- Code comments, docstrings, and every `docs/versioning/*` changelog —
  changelogs are a historical record of what was true at the time;
  rewriting them to match a later display convention would misrepresent
  that history the same way editing any other past changelog would.
- `docs/participant_guide.html`'s tie-break explanation ("player 0 wins
  by convention") — describes the actual internal fallback value
  `_determine_winner()` returns, not a rendered display string.
