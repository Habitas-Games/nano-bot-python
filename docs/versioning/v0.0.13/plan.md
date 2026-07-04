# v0.0.13 — Requirements Revision 2, Guide & Site Refresh Plan

**Status:** Complete
**Depends on:** [analysis.md](analysis.md)

---

## Approach

Documentation-only version: no engine, UI, or strategy code changes.
Verify every claim against the current code before writing it (grep for
the GUI seed, NanoAI-death handling, and 3–4-player CLI support rather
than trusting memory), and verify every suspected-stale doc line by
grep before editing it. The design inspiration informs *what* goes on
the roadmap but is never named in any shipped document.

## Order

1. Read the old requirements doc and the sibling port's full tables it
   delegated to; inventory what changed across v0.0.2–v0.0.12.
2. Rewrite `docs/requirements.md` as Revision 2: self-contained tables,
   per-requirement status markers, corrected-to-reality text, a §6
   Gameplay & UX review (findings only, each traceable to earlier
   verified evidence), a §7 roadmap (GAME-01..05, UX-01..04, two items
   marked ❓ as needing a design decision rather than pre-deciding
   them), and reframed M6/M7 milestones. Remove the origin mention.
3. Fix the six stale guide claims + add the demo-strategy reading path.
4. Fix `index.html`'s getting-started step 3 (match-window flow).
5. Fix `README.md`'s menu-flow paragraph and test count (296 → 301).
6. Validate: HTML tag-balance check on both pages, grep for remaining
   origin mentions and stale "player 0" label text, full pytest run to
   confirm the docs-only change touched nothing executable.

## Explicit non-goals for this version

- No implementation of any roadmap item (GAME-01..05, UX-01..04) — this
  version specs them; building them is M6/M7 work, and two (GAME-03,
  GAME-04) explicitly await a rule decision.
- No scrubbing of the sibling engine port's name from README/index —
  that's this project's own history, not the unnamed design
  inspiration.
- No edits to historical `docs/versioning/*` entries.
