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

# The product name shown to readers. The GitHub repository is still called
# nano-bot-python, so REPO_URL and any clone command keep that name — only
# the branding says "nano-bot".
BRAND = "nano-bot"
REPO_URL = "https://github.com/Habitas-Games/nano-bot-python"

# The menu, defined once for the whole site. Targets are written as if from
# the repository root; _href() rewrites them per page. Every page gets this
# exact list, in this order — that is the point.
NAV_ITEMS = [
    ("docs/lore.html",              "Briefing"),
    ("docs/learn_to_program.html",  "Learn to code"),
    ("docs/tutorial.html",          "Tutorial"),
    ("docs/participant_guide.html", "Guide"),
    ("docs/strategy_api.html",      "API"),
    ("index.html#start",            "Get started"),
]

# The landing page's own sections live in the footer rather than the nav, so
# the menu stays the same length everywhere instead of growing on one page.
FOOTER_ITEMS = NAV_ITEMS[:5] + [
    ("index.html",            "Home"),
    ("index.html#features",   "Features"),
    ("index.html#bots",       "Bot types"),
    ("index.html#contribute", "Contribute"),
    ("index.html#support",    "Support"),
]


def _href(target: str, in_docs: bool) -> str:
    """Rewrite a root-relative target for the page that will contain it."""
    if target.startswith("index.html"):
        anchor = target[len("index.html"):]
        if in_docs:
            return "../index.html" + anchor
        return anchor or "index.html"          # on the landing page: just the anchor
    return target[len("docs/"):] if in_docs else target


def nav_for(page: str) -> str:
    """`page` is the page's path from the repo root, e.g. 'docs/lore.html'."""
    in_docs = page.startswith("docs/")
    home = _href("index.html", in_docs)
    links = []
    for target, label in NAV_ITEMS:
        here = ' class="here"' if target == page else ""
        links.append(f'    <a href="{_href(target, in_docs)}"{here}>{label}</a>')
    return ("<nav>\n"
            f'  <div class="nav-logo"><a href="{home}">{BRAND}</a></div>\n'
            '  <div class="nav-links">\n'
            + "\n".join(links) + "\n"
            f'    <a href="{REPO_URL}" class="nav-gh">GitHub &#8599;</a>\n'
            "  </div>\n"
            "</nav>")


def footer_for(page: str) -> str:
    in_docs = page.startswith("docs/")
    links = [f'    <a href="{_href(t, in_docs)}">{label}</a>' for t, label in FOOTER_ITEMS]
    return ("<footer>\n"
            f'  <div class="footer-logo">{BRAND}</div>\n'
            '  <div class="footer-links">\n'
            + "\n".join(links) + "\n"
            "  </div>\n"
            '  <div class="footer-right">\n'
            "    MIT License<br>\n"
            '    <span style="color:var(--muted)">Built with Python + pygame</span>\n'
            "  </div>\n"
            "</footer>")


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
{nav_for("docs/" + out_name)}
<div class="doc">
<div class="doc-head">
  <h1>{html.escape(tagline)}</h1>
  <div class="tagline">{BRAND} &mdash; Habitas Games</div>
  {pill_html}
</div>
{note}
{body}
<hr>
<p style="color:var(--muted);font-size:13px">
  <a href="{md_name}">View the markdown source</a> &middot; this page is generated from it.
</p>
</div>
{footer_for("docs/" + out_name)}
</body>
</html>
"""
    return out_name, page


# Hand-written pages: only their <nav> and <footer> are managed here, so the
# menu can't drift between the landing page and the documentation. Everything
# else in these files is edited by hand as usual.
SHELL_PAGES = ["index.html", "docs/participant_guide.html", "docs/learn_to_program.html"]


def apply_shell(page: str, text: str) -> str:
    """Replace the nav and footer blocks of a hand-written page."""
    new = re.sub(r"<nav>.*?</nav>", lambda _: nav_for(page), text, count=1, flags=re.S)
    new = re.sub(r"<footer>.*?</footer>", lambda _: footer_for(page), new, count=1, flags=re.S)
    if "<nav>" not in text or "<footer>" not in text:
        raise SystemExit(f"{page}: expected a <nav> and a <footer> to keep in sync")
    return new


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

    for page in SHELL_PAGES:
        path = os.path.join(ROOT, page)
        existing = open(path, encoding="utf-8").read()
        updated = apply_shell(page, existing)
        if check:
            if existing != updated:
                stale.append(page + " (nav/footer)")
        elif existing != updated:
            open(path, "w", encoding="utf-8").write(updated)
            print(f"synced shell in {page}")
        else:
            print(f"{page} shell up to date")

    if check and stale:
        print("STALE (re-run tools/build_docs.py): " + ", ".join(stale))
        return 1
    if check:
        print("all generated docs are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
