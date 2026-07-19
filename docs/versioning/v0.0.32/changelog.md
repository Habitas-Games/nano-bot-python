# v0.0.32 Changelog

**Version:** 0.0.32 — docs render properly on the website

---

## Problem

Site links pointed at markdown files. A browser shows `.md` as unstyled
raw text, so "Read the briefing" and "Start the tutorial" — two of the
three hero buttons — dumped a wall of plain text on anyone who clicked
them. Six links were affected, plus a "README" link in Get Started.

The obvious fix (convert everything to HTML) breaks two things: GitHub
renders `.md` and shows `.html` as source, and `STRATEGY_API.md` exists
specifically to be pasted into an AI assistant. Hand-maintaining both
formats would drift.

## Fix — generate, don't duplicate

`tools/build_docs.py` renders `LORE.md`, `TUTORIAL.md` and
`STRATEGY_API.md` into styled pages (`lore.html`, `tutorial.html`,
`strategy_api.html`) matching the participant guide. Markdown stays the
single source of truth; the HTML is generated and marked
"do not edit by hand".

Dependency-free by design — the project only requires pygame, so the
converter covers exactly the subset these docs use (headings,
bold/italic, inline + fenced code, lists, tables, blockquotes, rules,
links). Intra-doc `.md` links are rewritten to their `.html`
counterparts; each page keeps a footer link to its markdown source.

- Site links (index, participant guide, learn-to-program) now point at
  the rendered pages.
- The README link now goes to GitHub's rendered README rather than the
  raw file.
- The AI-assistant card still points at the raw `STRATEGY_API.md`, which
  is the one place raw markdown is the *correct* target.

## Added — two guards

`tests/test_docs_build.py`:
- **staleness**: runs `build_docs.py --check`, so editing markdown and
  forgetting to rebuild fails the suite instead of shipping a stale
  site. (Verified it actually catches drift.)
- **no raw-markdown links**: asserts no site page sends a reader to a
  `.md` file, except the deliberate paste-me spec.

## Verification

```
$ pytest tests/  -> 364 passed (+2)
All six site pages: 0 broken links, 0 raw-markdown links.
Generated HTML tag-balance clean; code fences and tables converted.
Staleness guard confirmed to fail on a deliberately touched .md.
```
