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
