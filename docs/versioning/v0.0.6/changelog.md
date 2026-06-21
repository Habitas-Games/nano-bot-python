# v0.0.6 Changelog

**Version:** 0.0.6
**Status:** Complete
**Depends on:** [analysis.md](analysis.md), [plan.md](plan.md)

---

## Summary

Ported the Godot project's two HTML documents — a marketing landing page
and the participant rules/API guide — to `nano-bot-python`, neither of
which existed here before. Same structure and design as the originals;
every GDScript/Godot-specific claim re-verified against the actual
Python code and rewritten accurately rather than just relabeled. Also
corrects an asset-usage claim made earlier in this session and a CLI
flag mistake in three prior versions' verification steps.

## Added

- **`index.html`** (project root) — marketing landing page: hero,
  features, bot roster, a "Built with Python + pygame" section replacing
  the original's "Built with Godot 4," 3-step getting-started guide
  using `run.sh` and the real Python strategy skeleton, contribute
  section, and the same support/donation section (GitHub Sponsors,
  PayPal, De Una QR modal) as the original — same maintainer, so kept
  unchanged.
- **`docs/participant_guide.html`** — full rules and API reference:
  overview, quick-start, turn-phase table, map mechanics, all 8 bot
  stat cards, scoring formula and tie-break rules, full `NanoStrategy`/
  `BotProxy`/`MapInfo`/`HabitasPointInfo`/`AZNNodeInfo`/`CellInfo` API
  tables using the real Python method and property names, a walkthrough
  of `example_strategy_v2.py`, and strategy tips.
- **`assets/cover.png`, `assets/deuna_qr.png`, `assets/Tier 1 — Bot
  Sprites.png`, `assets/markers/injection_zone.png`** — copied from the
  Godot project; these are real assets used by the two HTML files above,
  not present in `nano-bot-python/assets/` before this version.

## Corrected

**Asset-usage claim from earlier in this session.** Said `habitas_owned.png`,
`injection_zone.png`, the four "Tier ..." sheets, `Tier 1 — Bot Sprites.png`,
`cover.png`, and `deuna_qr.png` were all unused in the Godot project. Only
checking `.gd`/`.tscn` files for references missed that `cover.png`,
`deuna_qr.png`, `Tier 1 — Bot Sprites.png`, and `injection_zone.png` are
all used — just in the two HTML files, not in the game itself. See
analysis.md §2 for the corrected table. `habitas_owned.png` actually is
used in the game (confirmed in v0.0.4), and the remaining "Tier ..."
sheets plus a separate plain `bots.png` are genuinely unused anywhere.

**CLI flag mistake in v0.0.3/v0.0.4/v0.0.5's verification steps.**
`headless_runner.py` reads `--strategy_a`/`--strategy_b`, not
`--strategy0`/`--strategy1` — the wrong flags used in every prior
"regression sweep" parsed without error but were silently never read,
so those runs simulated two strategy-less players scoring 0–0 the whole
time rather than verifying anything strategy-dependent. Full account
and why it doesn't affect those versions' actual (UI-only) findings is
in `v0.0.5/changelog.md`'s added correction note. Every CLI example in
this version's new HTML content and verification uses the correct flags.

## Confirmed accurate, restated for Python

Every fact below was checked against the live code (see analysis.md §4
for exact file references), not assumed from the GDScript original:
bot stats (`data/bot_types.json`), the `NanoStrategy`/`BotProxy`/
`MapInfo`/etc. API surface (`nanobot/api/*.py`), movement cost (density
2/3/4 turns, ±2 stream bonus/penalty, minimum 1), turn phase order, the
50ms strategy timeout, the 1500-turn cap, the `20 + 2×azn` / `5` scoring
formula, attack damage as a real `randint(1, max_damage)` range, and
that `example_strategy.py` (the starter) never builds anything while
`example_strategy_v2.py` is the one that demonstrates the full
build-collect-deliver loop the walkthrough section describes.

## Decided with the user, not guessed

The original HTML hardcodes a real GitHub repo URL throughout. Since
`nano-bot-python` has no repository yet, asked directly rather than
inventing one — per the user's choice, GitHub-specific CTAs (issues,
PRs, forking) show as inert "not yet available" text, "Browse
strategies" points at the local `strategies/` folder instead, and the
maintainer's personal support links (GitHub Sponsors, PayPal, De Una)
were kept since those identify the person, not the repository.

## Verification

```
$ python3 -c "html.parser tag-balance check on both files"
index.html unclosed tags remaining: []
docs/participant_guide.html unclosed tags remaining: []

$ python3 -c "every src=/href= in both files resolves to a real file"
index.html -> missing: NONE (one false positive: a #fragment-only anchor)
docs/participant_guide.html -> missing: NONE
```

**Honest gap, not glossed over:** attempted to render an actual
screenshot via `firefox --headless --screenshot` to visually confirm the
page layout, and it failed in this sandboxed environment (a snap-wrapped
Firefox profile lock, then a timeout on a fresh profile) with no other
headless browser available to fall back to. The checks above are real —
every fact was verified against the code, every link/image path
resolves, the HTML is structurally well-formed — but nobody has visually
confirmed the rendered layout in an actual browser yet. Recommend
opening `index.html` directly in a browser as a final check.

## Known gaps carried forward

- `assets/menu/` (main menu background + logo) and `assets/fx/` (event
  animations) remain unported into the pygame app itself — raised
  earlier in this session, separate from this version's HTML-only scope.
- `sprite_editor`'s MCP tools aren't loaded in the current session
  (registered in `~/.claude/.mcp.json` but not connected) — likely needs
  a Claude Code restart, not something fixable from within this session.
