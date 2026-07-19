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

STYLE = """
  :root {
    --bg:#0d0f16; --surface:#141720; --border:#1e2230; --accent:#38e570;
    --accent2:#407fff; --red:#ff4d40; --gold:#ffd91a; --muted:#8a8fa8;
    --text:#d8dce8; --heading:#eceef6; --code-bg:#0a0c12; --code-bdr:#252a3a;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:"Segoe UI",system-ui,sans-serif; background:var(--bg);
         color:var(--text); line-height:1.7; font-size:15px; }
  .page { max-width:900px; margin:0 auto; padding:40px 24px 80px; }
  header { border-bottom:1px solid var(--border); padding-bottom:28px; margin-bottom:32px; }
  .logo { font-family:monospace; font-size:42px; color:var(--accent); font-weight:700; letter-spacing:-1px; }
  .tagline { color:var(--muted); font-size:14px; margin-top:4px; }
  .pill { display:inline-block; background:var(--surface); border:1px solid var(--border);
          border-radius:99px; padding:3px 10px; font-size:12px; color:var(--muted);
          margin-top:10px; margin-right:6px; }
  .nav-strip { margin-bottom:32px; font-size:13px; color:var(--muted); }
  .nav-strip a { margin-right:14px; }
  h1 { font-size:26px; color:var(--heading); margin:44px 0 16px; }
  h2 { font-size:19px; color:var(--heading); margin:34px 0 12px;
       border-left:3px solid var(--accent); padding-left:12px; }
  h3 { font-size:15px; color:var(--accent); margin:24px 0 8px;
       text-transform:uppercase; letter-spacing:.06em; }
  p { margin-bottom:14px; }
  ul, ol { margin:0 0 14px 22px; }
  li { margin-bottom:5px; }
  a { color:var(--accent2); text-decoration:none; }
  a:hover { text-decoration:underline; }
  strong { color:var(--heading); }
  em { color:var(--gold); font-style:normal; }
  hr { border:none; border-top:1px solid var(--border); margin:36px 0; }
  blockquote { border-left:3px solid var(--accent2); background:var(--surface);
               border-radius:0 6px 6px 0; padding:12px 16px; margin:20px 0; color:var(--text); }
  blockquote p:last-child { margin-bottom:0; }
  code { font-family:"Cascadia Code","Fira Code",monospace; font-size:13px;
         background:var(--code-bg); border:1px solid var(--code-bdr);
         border-radius:4px; padding:1px 6px; color:var(--accent); }
  pre { background:var(--code-bg); border:1px solid var(--code-bdr); border-radius:8px;
        padding:20px; overflow-x:auto; margin:16px 0 24px; line-height:1.55; }
  pre code { background:none; border:none; padding:0; font-size:13px; color:var(--text); }
  table { width:100%; border-collapse:collapse; margin:16px 0 28px; font-size:13px; }
  th { background:var(--surface); color:var(--accent); font-size:11px; text-transform:uppercase;
       letter-spacing:.06em; text-align:left; padding:8px 12px; border-bottom:1px solid var(--border); }
  td { padding:7px 12px; border-bottom:1px solid var(--border); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
"""

NAV = ('<div class="nav-strip">'
       '<a href="../index.html">&larr; Home</a>'
       '<a href="lore.html">The briefing</a>'
       '<a href="learn_to_program.html">Learn to program</a>'
       '<a href="tutorial.html">Strategy tutorial</a>'
       '<a href="participant_guide.html">Participant guide</a>'
       '<a href="strategy_api.html">API reference</a>'
       '</div>')


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
<!-- GENERATED from docs/{md_name} by tools/build_docs.py — do not edit by hand. -->
<style>{STYLE}</style>
</head>
<body>
<div class="page">
<header>
  <div class="logo">nano-bot</div>
  <div class="tagline">{html.escape(tagline)}</div>
  {pill_html}
</header>
{NAV}
{note}
{body}
<hr>
<p style="color:var(--muted);font-size:13px;text-align:center">
  nano-bot &mdash; Habitas Games &middot;
  <a href="{md_name}">view the markdown source</a>
</p>
</div>
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
