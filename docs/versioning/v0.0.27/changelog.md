# v0.0.27 Changelog

**Version:** 0.0.27
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Adds a single, self-contained, LLM-consumable **strategy API spec** so
that handing it to an AI assistant produces working code. Prompted by a
Gemini-generated strategy that invented an entirely different API
(`NanoBotAPI`, `connect()`/`get_sensors()`/`send_action()`,
`api.move/shoot/harvest`, `{'x','y'}` dicts, 0–1000 coords) — none of
which exists. The participant guide's content is correct, but as styled
HTML behind "a link" it doesn't survive LLM consumption, and nothing in
it foreclosed the wrong mental model.

## Added

- **`docs/STRATEGY_API.md`** — the entire API in one plain-markdown
  file:
  - Opens by explicitly ruling out the wrong model (no network client,
    no `NanoBotAPI`, no sensors/tick loop, no position dicts, no
    0–1000 coordinates).
  - A minimal strategy that **loads, runs, and scores** — verified
    in-engine on both shipped maps (200/220 pts, wins both).
  - Full `BotProxy` (properties + command methods with the
    standing-on-the-cell / adjacency / range-12 rules), full `MapInfo`
    (including the dict-vs-object distinction for `visible_enemies` vs
    `habitas_points`), the info classes, the 8-bot stat table, and the
    scoring formula.
  - A "common mistakes (all of these are wrong)" section listing the
    exact `gemini.py` hallucinations beside the correct calls.

## Changed

- README's "Writing a strategy" section and the guide's §7 now point to
  the spec, with the instruction to **paste its contents** into the LLM
  rather than share a link.

## Verification

```
$ pytest tests/  -> 362 passed (docs + one markdown file; no code change)
Doc example extracted verbatim, loaded as a NanoStrategy, and run:
  bone_maze 200 pts (win), heart_chambers 220 pts (win).
```

## Note

`strategies/gemini.py` (the user's broken example) is left in place —
it's their file, not part of the shipped demos.
