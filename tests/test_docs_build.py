"""The website links to HTML pages generated from the markdown docs
(tools/build_docs.py). Markdown stays the single source of truth — GitHub
renders it and STRATEGY_API.md must stay markdown for pasting into an AI
assistant — so the generated HTML has to be regenerated whenever the
markdown changes. This test fails if someone edits the markdown and
forgets, which would otherwise ship a stale website silently."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_generated_docs_are_up_to_date():
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "build_docs.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, (
        "Generated docs are stale — run: python tools/build_docs.py\n" + result.stdout)


def test_site_pages_have_no_raw_markdown_links():
    """A browser shows .md as raw text, so no site page should send a
    reader to one — except the deliberate 'view the markdown source' /
    'paste this into your AI assistant' pointers."""
    import re
    pages = ["index.html", "docs/participant_guide.html", "docs/learn_to_program.html"]
    for page in pages:
        html = open(os.path.join(ROOT, page), encoding="utf-8").read()
        md_links = re.findall(r'href="([^"]*\.md)"', html)
        allowed = {"docs/STRATEGY_API.md", "STRATEGY_API.md"}   # the paste-me spec
        bad = [m for m in md_links if m not in allowed]
        assert not bad, f"{page} links to raw markdown: {bad}"


ALL_PAGES = ["index.html", "docs/lore.html", "docs/tutorial.html",
             "docs/strategy_api.html", "docs/participant_guide.html",
             "docs/learn_to_program.html"]


def _block(page, tag):
    import re
    html = open(os.path.join(ROOT, page), encoding="utf-8").read()
    m = re.search(rf"<{tag}>.*?</{tag}>", html, re.S)
    assert m, f"{page} has no <{tag}>"
    return m.group(0)


def test_every_page_has_the_same_menu():
    """The menu is defined once in tools/build_docs.py and stamped into
    every page. If someone hand-edits the nav on one page, the site goes
    back to feeling like two different websites — so fail loudly."""
    import re
    seen = {}
    for page in ALL_PAGES:
        labels = tuple(re.findall(r">([^<>]+)</a>", _block(page, "nav")))
        seen.setdefault(labels, []).append(page)
    assert len(seen) == 1, (
        "Pages disagree on the menu (run: python tools/build_docs.py)\n"
        + "\n".join(f"  {v}: {k}" for k, v in seen.items()))


def test_every_page_has_the_same_footer():
    import re
    seen = {}
    for page in ALL_PAGES:
        labels = tuple(re.findall(r">([^<>]+)</a>", _block(page, "footer")))
        seen.setdefault(labels, []).append(page)
    assert len(seen) == 1, (
        "Pages disagree on the footer (run: python tools/build_docs.py)\n"
        + "\n".join(f"  {v}: {k}" for k, v in seen.items()))


def test_menu_links_resolve():
    """Every nav/footer target must exist on disk — a consistent menu that
    404s is worse than an inconsistent one."""
    import re
    for page in ALL_PAGES:
        base = os.path.dirname(os.path.join(ROOT, page))
        for tag in ("nav", "footer"):
            for href in re.findall(r'href="([^"]+)"', _block(page, tag)):
                if href.startswith(("http", "#", "mailto")):
                    continue
                target = os.path.normpath(os.path.join(base, href.split("#")[0]))
                assert os.path.exists(target), f"{page} {tag} -> missing {href}"
