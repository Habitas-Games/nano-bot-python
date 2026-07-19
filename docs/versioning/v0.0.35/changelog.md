# v0.0.35 Changelog

**Version:** 0.0.35 — ways to support the project, including the free ones

---

## What was missing

The landing page already had a support section (GitHub Sponsors, PayPal,
De Una QR) and the v0.0.34 footer links to it from every page. Three
real gaps remained:

1. **The README had no support section at all** — and GitHub is where
   most people actually meet the project.
2. **No `.github/FUNDING.yml`**, so GitHub never showed its native
   "Sponsor" button at the top of the repository.
3. **Every listed way to help cost money.** For a project aimed at
   students learning to program, that's the wrong default: most of the
   audience can't donate, and the help they *can* give is worth more.

## Added

**Free ways to help**, now the larger block in the support section on
`index.html` and a matching section in the README: star the repository,
tell a student or teacher who'd enjoy it, report what breaks, share a
strategy or map you made, improve the docs. Framed honestly — a clear
bug report really is worth more than a small donation, and the copy says
so rather than treating it as a consolation prize.

**`.github/FUNDING.yml`** — enables GitHub's built-in Sponsor button,
pointing at the same two destinations the site already used
(`github/mnavas`, `paypal.me/warionv`). No new payment destinations were
invented; the file carries a comment to keep it in sync with
`index.html`.

**README `## Supporting the project`** — split into "costs nothing" and
"costs money", with the free list first.

It deliberately does not duplicate the Contribute section (bugs,
features, pull requests); the support block cross-links to it instead.

## Verification

```
$ pytest tests/  -> 367 passed
index.html: valid HTML, balanced markup in the new block, 0 broken links
            (all in-page anchors resolve to a real id).
build_docs.py --check: all generated docs and page shells up to date.
```
