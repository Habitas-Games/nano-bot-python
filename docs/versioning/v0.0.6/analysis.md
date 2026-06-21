# v0.0.6 — Marketing Site & Participant Guide Port Analysis

**Status:** Complete
**Depends on:** [../v0.0.5/changelog.md](../v0.0.5/changelog.md)

---

## 1. Trigger

User question: "what happened with the assets on the original project, can
they be used in this one?" led to an asset-usage audit (§2). A follow-up —
"the assets were used on the html files that should be redone for this
project" — pointed at two files this audit had initially missed:
`nano-bot/index.html` (a marketing landing page) and
`nano-bot/docs/participant_guide.html` (the rules/API reference for
competitors). Neither exists in `nano-bot-python`.

## 2. Correcting the asset audit: not all "unused" assets were unused

The asset audit immediately before this version checked only `.gd`/`.tscn`
files for references and concluded several files were dead weight:
`cover.png`, `deuna_qr.png`, `Tier 1 — Bot Sprites.png`,
`markers/injection_zone.png`. Grepping the two HTML files directly showed
this was wrong — all four are real, used assets:

| Asset | Used in |
|---|---|
| `cover.png` | Both HTML files' hero image |
| `deuna_qr.png` | `index.html`'s donation modal |
| `Tier 1 — Bot Sprites.png` | `participant_guide.html`'s bot-roster figure |
| `markers/injection_zone.png` | `participant_guide.html`'s injection-zone illustration (never used in actual game rendering in either project — that part of the original claim was correct) |

Genuinely unused anywhere in either project, confirmed by grepping both
`.gd`/`.tscn` files and both HTML files: the other three "Tier ..." sheets
(`Tier 1 Map tiles.png`, `Tier 1 Map Markers.png`, `Tier 2 — UI & HUD.png`,
`Tier 3 — Main Menu.png`, `Tier 3 — Event VFX.png`) and a separate plain
`bots.png` distinct from the roster image above.

All four real, used assets were copied into `nano-bot-python/assets/`
(previously only `tiles/`, `bots/`, and three of four `markers/` files had
been copied during the original port).

## 3. `sprite_editor`: an MCP tool, not part of either project

A separate mention — "there is also the sprite_editor folder useful to
edit assets" — pointed at `/home/mario/godot/sprite_editor/server.py`, a
PIL-based MCP server (crop/resize/trim/tint/slice/composite/etc., 21
tools) registered in `~/.claude/.mcp.json` as `sprite-editor`. Its Python
dependencies (`mcp`, `Pillow`) are installed and importable, but its
tools weren't loaded in the current session — most likely needs a Claude
Code restart to pick up a server registered after the session started.
Not part of this version's changes; noted for whoever next needs to
crop/recolor a sprite.

## 4. Scope: straight port, content corrected against the live codebase

The user's explicit choice (asked directly, since "Python-ized straight
port" vs. "just one of the two files" vs. "describe what you want" were
all reasonable readings of "redone for this project"): port both files,
same structure and sections, with every GDScript/Godot-specific claim
replaced by the Python equivalent — not copied-and-relabeled.

Every technical claim in the original HTML was re-verified against
`nano-bot-python`'s actual code before being restated, not just
syntax-translated:

- Bot stats (`data/bot_types.json`) — exact match, no changes needed.
- Strategy API method/property names (`nanobot/api/*.py`) — exact 1:1
  match with the GDScript originals' names.
- Movement cost formula, stream bonus/penalty, minimum cost
  (`map_data.py`) — exact match (2/3/4 turns, ±2 stream, min 1).
- Turn phase order, 50ms strategy timeout, 1500 max turns, scoring
  formula `20 + 2×azn` / `5` (`simulation_core.py`) — exact match.
- Attack damage range (`_resolve_attacks`'s `randint(1, max_damage)`) —
  confirms the guide's "Damage: 1–5" claim is a real random range, not a
  flat value.
- Map dimensions — the original guide stated a "default 50×50"; the
  actual bundled maps are 80×80 and 60×60 with no single canonical
  default (each map JSON declares its own size), so this version states
  it generically instead of repeating an unverified specific number.
- `example_strategy.py` vs. `example_strategy_v2.py` — confirmed by
  reading both files directly that the *simple* starter
  (`example_strategy.py`) never builds anything and always scores 0,
  while the walkthrough section's described behavior (build a collector,
  claim a Habitas Point, ferry AZN) matches `example_strategy_v2.py`
  specifically — the guide's walkthrough section now names the right
  file instead of implying the starter does this.

## 5. A verification mistake caught while researching this version

While re-running the project's documented CLI command to confirm the
"Debugging tip" callout's wording, the headless runner produced a
real score split (0 vs. 160) — but every prior "regression sweep" run in
this session's v0.0.3–v0.0.5 changelogs had shown **both** players
scoring 0, using `--strategy0`/`--strategy1` instead of the CLI's actual
`--strategy_a`/`--strategy_b` flags. `headless_runner.py`'s argument
parser accepts any `--key value` pair without validating it against the
flags it actually reads, so the wrong flag names parsed without error
and were silently never read — every one of those "regression" runs
actually simulated two strategy-less players the whole time. See
v0.0.5/changelog.md's added correction note for the full account and why
it doesn't call any of those versions' UI findings into question (none
of them depended on the CLI). Fixed here by using the correct flags in
this version's own verification and in every CLI example written into
the new HTML content, so the mistake isn't propagated into participant-
facing documentation.

## 6. Repository URL

The original HTML hardcodes `https://github.com/Habitas-Games/nano-bot`
throughout (nav, hero, footer, issue/PR templates) — confirmed real via
that project's own `README.md` (a live GitHub Pages site), not invented.
`nano-bot-python` has no remote configured and no public repository yet.
Asked the user directly rather than guessing or inventing a URL for a
repo that doesn't exist; their answer was to use local/placeholder links
for now (e.g., "Browse strategies" points at the local `strategies/`
folder; "Report a bug"/"Fork"/"PR" show as inert "not yet available"
text) so a real URL can be dropped in later without restructuring
anything. Personal support links (GitHub Sponsors, PayPal, De Una) were
kept unchanged since they identify the maintainer, not the repository.
