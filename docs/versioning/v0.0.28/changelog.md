# v0.0.28 Changelog

**Version:** 0.0.28 — `example_adaptive`, the advanced demo

---

## Why

Measurement showed no map change could "make sophisticated strategies
shine" because **there were no sophisticated strategies** — the
hold-all bonus was completely inert (nobody ever holds all points), and
every demo plays one fixed idea regardless of what it sees. The ceiling
had to be raised first.

## Added — `strategies/example_adaptive.py`

The first demo that reads the map and adapts. Four behaviours, in
priority order (survive first, then grow):

1. **Scouts** — builds a NanoExplorer watchtower early; under fog
   nothing else can see a raider coming (scan 30 vs ~0).
2. **Defends reactively** — reactive NanoWall on the firing line +
   collector shoot-back (the only pattern measured to reliably beat
   `example_combat`).
3. **Clears white cells** — `defend()` works on hazards, and they never
   respawn, so ~15-25 turns of fire permanently de-taxes a supply line.
   **No other strategy does this.** Verified in a trace: 27 shots at
   white cells, 2 patrols destroyed.
4. **Expands only when unthreatened** — claims a 2nd Habitas Point once
   the first is fed, defended and quiet (two needles out-score one
   fortified needle; expanding under pressure is how `full_roster`
   loses).

## Result — sophistication now wins, without a tyrant

3-map, 9-strategy, 108-match tournament:

```
1 adaptive     21W  3L  5180 pts   <- champion
2 defense      17W  7L  4820
3 ip_creator   17W  7L  4530       <- beats adaptive 2-1 (its counter)
4 full_roster  13W 11L  5400
5 strategy_v2  12W 12L  4690
6 combat       12W 12L  3690
...
strict kings: NONE — no strategy beats the whole field
```

The advanced strategy tops the table *and* still has a counter, so the
field stays competitive. 362 tests pass.
