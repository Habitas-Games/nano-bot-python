# v0.0.13 Changelog

**Version:** 0.0.13
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Documentation-only release. `docs/requirements.md` rewritten as a
self-contained Revision 2 with per-requirement statuses, a gameplay/UX
review, and a concrete M6/M7 roadmap; the participant guide, landing
page, and README purged of every claim that went stale between v0.0.7
and v0.0.11. The design inspiration is no longer named anywhere in the
project's shipped documents.

## Changed

- **`docs/requirements.md`** — full rewrite (Revision 2):
  - Self-contained: no longer delegates its requirement tables to the
    sibling engine port's doc; origin mention removed per request.
  - Every requirement carries a status (✅/🟡/⬜/❓) matching verified
    current behavior — including the real turn-phase order, the real
    tie-break chain, generalized transfers (BOT-10), working
    `open_ip()`, the random spawn fallback (MAP-06), and the
    match-window workspace (VIS-07).
  - New §6 **Gameplay & UX review**: five findings, each traceable to
    evidence produced earlier in this project's history — no PvE
    pressure, Scan is a dead stat (fog of war never implemented),
    combat has no counterplay (14–0 shutouts), contested Habitas
    Points resolve silently, and spectator gaps (no event VFX, GUI
    matches hardcode seed 0).
  - New §7 roadmap: GAME-01 fog of war, GAME-02 immune-system hazards,
    GAME-03 combat counterplay (❓ line-of-sight rule proposed, not
    decided), GAME-04 habitas exclusivity (❓), GAME-05 third map,
    UX-01 replay browser, UX-02 zone owner selector, UX-03 event VFX +
    menu art, UX-04 seed control. M6 "Make it a game" / M7 "Polish &
    spectate" reframed around these.
- **`docs/participant_guide.html`** — six stale claims fixed:
  quickstart now describes the match-window pickers + Restart (moved
  there in v0.0.9); pan documented as left-drag first (v0.0.7);
  `transfer_to` documents container targets and relay chains (v0.0.8);
  the starter strategy correctly described as planting a needle for a
  5 pts/turn baseline (v0.0.10); tie-break fallback says "Player 1"
  (v0.0.11); the debugging tip no longer claims a nonexistent "Load
  Replay" picker. Added a "one demo per mechanic" reading path for the
  six v0.0.8 example strategies, which the guide had never mentioned.
- **`index.html`** — getting-started step 3 now describes the
  match-window flow instead of main-menu dropdowns.
- **`README.md`** — menu-flow paragraph updated to the match-window
  flow; test count corrected (296 → 301).

## Verification

```
$ pytest tests/
301 passed in 0.93s          # docs-only change; suite untouched
```

- HTML tag-balance check: both pages report zero unclosed/mismatched
  tags.
- `grep -ri` across README, index.html, participant_guide.html,
  requirements.md: zero mentions of the original competition or its
  sponsor; zero remaining "player 0" label text in the guide.
- Facts encoded in the new requirements verified against code this
  round rather than recalled: GUI seed hardcoded to 0 in both
  `main_menu.py` and `playback_viewer.py`; NanoAI death stops new
  actions but not in-flight movement (`_call_strategies` skip +
  unconditional `_advance_movement`); headless CLI accepts
  `--strategy_c/_d` (SIM-08's "up to 4 via CLI").

## Known gaps carried forward

- Everything in §7 of the new requirements is specced, not built —
  GAME-03 and GAME-04 additionally await a rule decision.
- No unit tests for the pygame rendering/widget layer — unchanged gap.
