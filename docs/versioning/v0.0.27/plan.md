# v0.0.27 — LLM-Consumable API Spec Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Order

1. Read the actual API surface from source (`nano_strategy`,
   `bot_proxy`, `map_info`, `habitas_point_info`, `azn_node_info`,
   `cell_info`, `bot_types.json`) so every signature/field is exact.
2. Write `docs/STRATEGY_API.md`: wrong-model disclaimer first; verified
   minimal example; full BotProxy / MapInfo / info-class reference; bot
   stat table; scoring; a "common mistakes" section mirroring the exact
   `gemini.py` hallucinations.
3. **Verify the example in-engine** — extract it verbatim, load it,
   run it on both maps, confirm it scores. Fix if it doesn't (it did:
   nearest-point fix so it scores on Heart Chambers too).
4. Point README + guide §7 at the spec, instructing to paste its
   contents (not a link).
5. Full pytest (docs-only, but confirm nothing broke); commit + push.

## Explicit non-goals

- Rewriting the participant guide into markdown — it stays the
  human-facing document; the spec is the machine-facing one.
- Removing `strategies/gemini.py` — it's the user's file; left as-is.
- Any engine/API change — the API is fine; the gap was consumability.
