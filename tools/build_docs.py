#!/usr/bin/env python3
"""Render the markdown docs into styled HTML pages for the website.

Why this exists: the project publishes through two channels with opposite
needs. GitHub renders .md and shows .html as source; a browser does the
reverse. And STRATEGY_API.md has to stay markdown because its whole job
is being pasted into an AI assistant.

So markdown stays the single source of truth and this generates the
HTML the site links to — no hand-maintained duplicates to drift apart.

Usage:  python tools/build_docs.py        (writes docs/*.html)
        python tools/build_docs.py --check  (fails if output is stale)

Deliberately dependency-free: the project only requires pygame, and a
markdown package for three files isn't worth it. The converter covers
exactly the subset these documents use (headings, bold/italic, inline
code, fenced code, lists, tables, blockquotes, rules, links) — if you
write markdown that needs more, extend it here rather than hand-editing
generated HTML.
"""

from __future__ import annotations

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

# md filename -> (output html, browser title, tagline, pills)
PAGES = {
    "LORE.md": ("lore.html", "The Trials — nano-bot", "The briefing",
                ["Story", "Why any of this matters"]),
    "TUTORIAL.md": ("tutorial.html", "Strategy Tutorial — nano-bot", "Build a competitive strategy",
                    ["4 stages", "Every number measured", "Assumes basic Python"]),
    "STRATEGY_API.md": ("strategy_api.html", "Strategy API — nano-bot", "Complete API reference",
                        ["Every command", "One page"]),
}
# links between generated docs get rewritten to their .html counterparts
LINK_MAP = {md: out for md, (out, *_rest) in PAGES.items()}

STYLE_HREF = "../assets/site.css"   # shared shell: tokens, nav, footer, doc typography

NAV = """<nav>
  <div class="nav-logo"><a href="../index.html">nano-bot</a></div>
  <div class="nav-links">
    <a href="lore.html"{here_lore}>Briefing</a>
    <a href="learn_to_program.html"{here_learn}>Learn to code</a>
    <a href="tutorial.html"{here_tut}>Tutorial</a>
    <a href="participant_guide.html"{here_guide}>Guide</a>
    <a href="strategy_api.html"{here_api}>API</a>
    <a href="https://github.com/Habitas-Games/nano-bot-python" class="nav-gh">GitHub &#8599;</a>
  </div>
</nav>"""

FOOTER = """<footer>
  <div class="footer-logo">nano-bot</div>
  <div class="footer-links">
    <a href="../index.html">Home</a>
    <a href="lore.html">Briefing</a>
    <a href="learn_to_program.html">Learn to code</a>
    <a href="tutorial.html">Tutorial</a>
    <a href="participant_guide.html">Guide</a>
    <a href="strategy_api.html">API</a>
  </div>
  <div class="footer-right">
    MIT License<br>
    <span style="color:var(--muted)">Built with Python + pygame</span>
  </div>
</footer>"""


def nav_for(out_name: str) -> str:
    keys = {"lore.html": "here_lore", "learn_to_program.html": "here_learn",
            "tutorial.html": "here_tut", "participant_guide.html": "here_guide",
            "strategy_api.html": "here_api"}
    marks = {v: "" for v in keys.values()}
    if out_name in keys:
        marks[keys[out_name]] = ' class="here"'
    return NAV.format(**marks)


def _inline(text: str) -> str:
    """Inline markdown -> HTML. Code spans are protected first so their
    contents never get treated as markup."""
    spans: list[str] = []

    def stash(m):
        spans.append(html.escape(m.group(1)))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)

    def link(m):
        label, href = m.group(1), m.group(2)
        base = href.split("#", 1)[0]
        if base in LINK_MAP:
            href = href.replace(base, LINK_MAP[base])
        return f'<a href="{href}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]          # row 1 is the |---| separator
    out = ["<table>", "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):                       # fenced code
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        if re.match(r"^\|.*\|\s*$", line) and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            buf = []
            while i < len(lines) and line.strip().startswith("|"):
                buf.append(lines[i])
                i += 1
                if i < len(lines):
                    line = lines[i]
            out.append(_table(buf))
            continue

        if re.match(r"^\s*(---|\*\*\*|___)\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = min(len(m.group(1)), 3)
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>" + _inline(" ".join(buf)) + "</p></blockquote>")
            continue

        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines) and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])
                                       or (items and lines[i].startswith("  ") and lines[i].strip())):
                if re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i]):
                    items.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()   # continuation line
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(t)}</li>" for t in items) + f"</{tag}>")
            continue

        if not line.strip():
            i += 1
            continue

        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|```|>|\s*[-*]\s+|\s*\d+\.\s+|\|)", lines[i]) \
                and not re.match(r"^\s*(---|\*\*\*|___)\s*$", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def render_page(md_name: str) -> tuple[str, str]:
    out_name, title, tagline, pills = PAGES[md_name]
    md = open(os.path.join(DOCS, md_name), encoding="utf-8").read()
    body = md_to_html(md)
    pill_html = "".join(f'<span class="pill">{html.escape(p)}</span>' for p in pills)
    note = ""
    if md_name == "STRATEGY_API.md":
        note = ('<blockquote><p>Using an AI assistant? Paste the '
                '<a href="STRATEGY_API.md">raw markdown version</a> into the chat rather than '
                'this page — it is written to be machine-read.</p></blockquote>')
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<!-- GENERATED from docs/{md_name} by tools/build_docs.py \u2014 do not edit by hand. -->
<link rel="stylesheet" href="{STYLE_HREF}">
</head>
<body>
{nav_for(out_name)}
<div class="doc">
<div class="doc-head">
  <h1>{html.escape(tagline)}</h1>
  <div class="tagline">nano-bot &mdash; Habitas Games</div>
  {pill_html}
</div>
{note}
{body}
<hr>
<p style="color:var(--muted);font-size:13px">
  <a href="{md_name}">View the markdown source</a> &middot; this page is generated from it.
</p>
</div>
{FOOTER}
</body>
</html>
"""
    return out_name, page


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for md_name in PAGES:
        out_name, page = render_page(md_name)
        path = os.path.join(DOCS, out_name)
        existing = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if check:
            if existing != page:
                stale.append(out_name)
        elif existing != page:
            open(path, "w", encoding="utf-8").write(page)
            print(f"wrote docs/{out_name}")
        else:
            print(f"docs/{out_name} up to date")
    if check and stale:
        print("STALE (re-run tools/build_docs.py): " + ", ".join(stale))
        return 1
    if check:
        print("all generated docs are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
