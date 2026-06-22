# v0.0.11 — 1-Indexed Player Labels Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Add 1 only at the point of display (an f-string), never to the
underlying value — `pid`, `bot["owner"]`, `log.winner_id` keep flowing
through every dict key, comparison, and color lookup exactly as before.
Grep for every occurrence first to find all of them in one pass rather
than fixing one and discovering more later.

## Order

1. `grep -rn "Player [0-9]\|player {.*id}\|f\"Player\|f'Player"` across
   `nanobot/`, `strategies/`, `docs/*.html`, `README.md` to enumerate
   every candidate site.
2. Triage each hit: a rendered UI label (fix) vs. a code comment, CLI
   tool message, internal engine log line, or historical changelog
   (leave alone) — see analysis.md §3 for the exact list.
3. Fix the 5 real UI sites: `playback_viewer.py`'s HUD score line,
   winner line, inspector owner line; both screens' match-summary
   message string; `zone_tool.py`'s status text.
4. Verify visually, not just by reading the diff: render the playback
   viewer's final frame with the inspector open and check all four
   labels in one screenshot.

## Verification

```
$ pytest tests/
299 passed in 0.97s

$ python tests/check_editor.py
ALL OK
```

Screenshot of the playback viewer (last frame, a bot selected) showing
all four fixed labels at once: "Player 1: 15 pts", "Player 2: 110 pts",
"Winner: Player 2", "Owner: Player 1" — matching the picker buttons'
existing "P1:"/"P2:" labels for the first time. Confirmed the main
menu's match-summary message separately. Confirmed the CLI tool's stdout
(`run_headless.py`) deliberately still reads "player 0"/"player 1" per
analysis.md §3.

## Explicit non-goals for this version

- No change to any JSON replay format, dict key, or internal player ID —
  purely a display-string change.
- No change to CLI tool output, engine log lines, or any historical
  changelog under `docs/versioning/`.
