# v0.0.31 Changelog

**Version:** 0.0.31 — "Learn to Program with Nano-Bot"

---

## Added — `docs/learn_to_program.html`

A beginner programming course that uses the swarm as the vehicle. The
existing tutorial assumes you can already read Python; this one assumes
nothing. Eight lessons, each concept introduced *because the bots need
it*:

| Lesson | Programming concept |
|---|---|
| Setup | running it, and reading the Events panel when it breaks |
| 1 Giving one order | calling functions, arguments |
| 2 Naming things | variables, tuples, indexing, attributes |
| 3 Choosing | `if`/`elif`/`else`, indentation, `==` vs `=` |
| 4 Doing it to everyone | `for` loops; one-order-per-bot |
| 5 Collections | lists, objects, dicts, list comprehensions |
| 6 Your own instructions | `def`, `return`, "best so far" |
| 7 Remembering | `self` / state across turns, and the oscillation bug it prevents |
| 8 Your first real swarm | a complete working strategy |

It closes with a table mapping each thing they used to its real name and
where they'll meet it again (SQL, data science, every algorithm), plus
the point that their program has to keep working unattended for 1500
turns — "that is the actual job of a programmer, and you've now done it."

**Verified:** the Lesson 8 strategy was extracted from the rendered HTML
(spans stripped, entities decoded), loaded, and run on all three shipped
maps — it fills its implant to 90–100 AZN, scores 200–220/turn, and wins
every map against the starter. The page's claim was corrected from a flat
"220" to the accurate "200–220" after measuring.

## Changed — cross-linking

The page is reachable from everywhere it should be: landing-page nav +
its own card, the participant guide's opening, the tutorial's
prerequisite note, the README, and the end of the lore briefing. All five
of its own outbound links verified to resolve.

## Fixed

- README claimed 321 unit tests; the suite is 362.

## Verification

```
$ pytest tests/  -> 362 passed
Lesson 8 code extracted from HTML and run: 200-220 pts, wins all 3 maps.
HTML tag-balance clean (learn_to_program, index, participant_guide).
All internal links in the new page resolve.
```
