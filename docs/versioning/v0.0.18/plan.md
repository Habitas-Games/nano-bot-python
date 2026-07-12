# v0.0.18 — Bot Documentation Implementation Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Ground truth first: read the engine's action handlers and BotProxy
before writing either artifact, so the guide and the in-app sentences
describe what the code does, not what memory says it does. Data
before UI: the sentences go into the bot-stats data file so both
current and future surfaces read the same words.

## Order

1. **`data/bot_types.json`**: a `description` field per type — one
   plain-language sentence each. `bot_type_registry.get_description()`
   exposes it (registry already tolerates unknown keys).
2. **Viewer Bot Inspector** (`playback_viewer.py`): description
   rendered between the type line and the stats, greedy-wrapped to
   the panel width (3-line budget); panel bottom-anchored with
   `INSPECTOR_DESC_EXTRA` claimed only while a bot is selected;
   `_inspector_top()` shared with the Events-ticker clip so the
   v0.0.15 no-overlap invariant holds at every window size.
3. **Guide** (`participant_guide.html`): "Programming each bot"
   section after the stat cards — two cross-cutting callouts
   (one-action-per-turn/last-call-wins; stand-on-the-cell logistics)
   and eight subsections with verified preconditions, the proven
   patterns from the shipped demos, and paste-ready snippets using
   only the real API (`get_cell().is_bone`, `enemy["position"]`).
4. **Verification**: pytest; scripted check (all types have short
   sentences; panel grows only on selection; wrap fits); screenshots
   at 1280×800 and 1024×640; guide HTML tag-balance parse.
5. **Docs**: VIS-05 row notes the inspector description; this folder.

## Explicit non-goals

- No engine/balance changes — documentation and one HUD panel only.
- Editor doesn't show bot descriptions (it places terrain/elements,
  not bots).
- Bot-card blurbs in the guide keep their own wording — the cards are
  a stats quick-reference; the JSON sentence is the spectator-facing
  one-liner.
