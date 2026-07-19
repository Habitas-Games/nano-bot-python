# v0.0.33 Changelog

**Version:** 0.0.33 — one design system across the whole site

---

## Problem

The site was running two unrelated designs. The landing page had a
sticky nav, section rhythm and a footer; the documentation pages had a
big monospace logo block, pills, a row of plain text links and no footer
at all. Clicking "Guide" or "Learn to code" felt like leaving the
product for someone else's website.

The lore was also hard to find: the nav item labelled "Briefing" pointed
at a *section anchor* on the landing page, not at the full mission text
in `lore.html`.

## Fix — a shared shell

**`assets/site.css`** is now the single source of truth for the design
tokens, the sticky nav, the footer and documentation typography. Every
page links it; page-specific styling stays inline.

- `index.html` now links the shared sheet and its duplicated
  tokens/reset/body/nav/footer rules were removed (all of its own
  landing-page styling — hero, cards, steps, bots, support — is
  untouched).
- **All five doc pages** (`participant_guide`, `learn_to_program`, and
  the generated `lore`, `tutorial`, `strategy_api`) now carry the
  identical sticky nav and footer, wrapped in a `.doc` container that
  keeps a readable measure while using the same colours, fonts and
  chrome as the landing page.
- `tools/build_docs.py` emits that shell, so regenerated pages stay
  consistent by construction. The current page is marked in the nav
  (`.here`).

## Fixed — the lore is findable

- Nav "Briefing" now goes to **`docs/lore.html`** (the full mission
  text) on every page, instead of a landing-page anchor.
- The nav gained Tutorial and API entries, so all five documents are one
  click away from anywhere — including from inside the app's docs.

## Verification

```
$ pytest tests/  -> 364 passed
All 6 pages: valid HTML, 0 broken links, nav + footer + shared CSS present.
Confirmed index.html kept every page-specific rule while the shared
rules moved out; doc-page navs are byte-identical to each other.
```
