# v0.0.36 Changelog

**Version:** 0.0.36 — Support goes back into the always-visible menu

---

## Regression from v0.0.34

Making the menu identical across all six pages meant moving the landing
page's extra nav items into the footer. **Support went with them** — so
the only way to reach it became scrolling to the bottom of a page.

That's backwards. Support is exactly the link that has to be reachable
at any moment, from anywhere, without hunting for it. It was easy to
find before and it should have stayed that way.

## Fix

**Support is back in the nav**, on every page:

> Briefing · Learn to code · Tutorial · Guide · API · Get started · ♥ Support · GitHub

Because the menu is generated from a single `NAV_ITEMS` list, adding it
once put it on all six pages with the right relative path (`#support` on
the landing page, `../index.html#support` from the docs) — and the
v0.0.34 consistency tests still pass, which is the whole point of having
built it that way.

It's styled apart from the navigation links (gold, with a ♥) so it reads
as an ask rather than another destination — tinted rather than shouting.
Features, Bot types and Contribute stay in the footer; those are
browsing, not asks.

## Verification

```
$ pytest tests/  ->  367 passed
Support link present in the nav of all 6 pages, each with the correct
relative target. Menu/footer consistency guards still pass.
```
