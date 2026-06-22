# v0.0.11 Changelog

**Version:** 0.0.11
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Player labels in the running app now read "Player 1"/"Player 2" instead
of "Player 0"/"Player 1" — display only, the underlying 0-indexed
player IDs are unchanged everywhere they're actually data (dict keys,
`winner_id`, `bot["owner"]`, every JSON replay file). This also fixes an
inconsistency that already existed: the playback viewer's map/strategy
picker buttons (v0.0.7) already showed 1-indexed "P1:"/"P2:" while every
other label on the same screens showed the raw 0-indexed value.

## Changed

- **`nanobot/ui/playback/playback_viewer.py`**: the HUD's per-player
  score line ("Player {pid+1}: ..."), the "Winner: Player {...+1}" line,
  and the Bot Inspector's "Owner: Player {...+1}" line.
- **`nanobot/ui/playback/playback_viewer.py`** and
  **`nanobot/ui/main_menu.py`**: both screens' match-summary message
  string ("... winner: Player {winner_id+1}").
- **`nanobot/ui/map_editor/tools/zone_tool.py`**: the status-bar text
  for the Place Zone tool now reads "player 1" instead of "player 0" —
  new zones still default to the engine's player index 0 internally
  (`map_document_ops.place_zone`'s `player: int = 0`), only the
  displayed text changed.

## Verification

```
$ pytest tests/
299 passed in 0.97s

$ python tests/check_editor.py
ALL OK

$ python run_headless.py --map maps/simple_tissue.json \
    --strategy_a strategies/example_strategy.py \
    --strategy_b strategies/example_strategy_v2.py --seed 1
HeadlessRunner: winner — player 1   # CLI output intentionally unchanged, see analysis.md §3
  player 0: 15 pts
  player 1: 110 pts
```

Rendered the playback viewer's final frame with a bot selected and
visually confirmed all four fixed labels at once: "Player 1: 15 pts",
"Player 2: 110 pts", "Winner: Player 2", "Owner: Player 1" — consistent
with the picker buttons' existing "P1:"/"P2:" for the first time.
Separately confirmed the main menu's own match-summary message
("... winner: Player 1").

## Known gaps carried forward

- Combat-effectiveness/defense-design question (v0.0.10) — still open.
- Contested-Habitas-Point scoring resolution (v0.0.8) — still open.
- No unit tests for the pygame rendering/widget layer — unchanged gap
  from every prior version.
