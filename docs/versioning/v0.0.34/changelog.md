# v0.0.34 Changelog

**Version:** 0.0.34 — the project is called **nano-bot**, and the menu is
the same on every page

---

## Renamed to nano-bot

The product is now called **nano-bot** everywhere a reader can see it:
page titles, the nav logo, the footer, the README heading and body prose.

What deliberately did *not* change: the GitHub URL
(`github.com/Habitas-Games/nano-bot-python`), the `cd nano-bot-python`
line in the quick-start, and the directory name in the project-layout
diagram. Those are facts about the repository, and rewriting them would
have shipped a clone command that doesn't work.

## One menu, defined once

v0.0.33 gave every page the same *styling* but not the same *menu*: the
landing page carried 11 nav links (its own section anchors mixed in with
the doc links) while the documentation pages carried 6, and the two
footers listed different things. Same paint, different furniture.

Now the menu is **identical on all six pages**:

> Briefing · Learn to code · Tutorial · Guide · API · Get started · GitHub

The landing page's own sections (Features, Bot types, Contribute,
Support) moved to the footer, which is also now identical everywhere. So
the menu no longer grows on one page, and every section is still one
click away from anywhere.

### It is generated, not hand-synced

`tools/build_docs.py` now owns the nav and footer for **all six pages**,
including the three hand-written ones (`index.html`,
`participant_guide.html`, `learn_to_program.html`) — it rewrites just
their `<nav>` and `<footer>` blocks and leaves the rest alone. The menu
is a single list (`NAV_ITEMS`) in that file; `_href()` rewrites each
target for the page that will contain it, so the landing page gets
`docs/lore.html` and a doc page gets `lore.html` from the same
definition.

## Tests

Three new guards in `tests/test_docs_build.py`, because "consistent"
only stays true if something checks:

- `test_every_page_has_the_same_menu` — all six navs must agree
- `test_every_page_has_the_same_footer` — same for footers
- `test_menu_links_resolve` — every nav/footer target must exist on disk
  (a consistent menu that 404s is worse than an inconsistent one)

Verified the guard actually bites: hand-editing one nav label on
`index.html` fails both the menu test and the staleness check; reverting
passes.

```
$ pytest tests/   ->  367 passed
All 6 pages: valid HTML, 0 broken links, 1 distinct nav label set.
```
