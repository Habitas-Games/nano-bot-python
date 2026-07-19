# v0.0.30 Changelog

**Version:** 0.0.30 — lore & motivation pass

---

## Why

The platform read as a pure spec: "turn-based AI programming
competition… outscore your opponent." True, but it gave a newcomer no
reason to care and no identity to step into. The mechanics already
contained a story — nanobots, a patient's bloodstream, an immune system
that can't tell friend from foe — it just was never told.

## Added — `docs/LORE.md`, "The Trials"

A briefing where **every rule is diegetic** — nothing is an arbitrary
game mechanic:

| Mechanic | In the fiction |
|---|---|
| AZN | the therapeutic compound; breaks down if injected at large, so it must be hauled molecule by molecule |
| Habitas Point / NanoNeedle | a receptor site, and the implant that holds the dose there |
| Empty vs fed needle (5 vs 20+2×AZN) | an implant that's landed vs one actually delivering |
| White cells | the patient's own defences, working correctly, with your swarm in the way — not malice |
| Bloodstreams (one-way) | the fastest roads in the body; you can't turn around on one |
| Fog of war | your bots sense only what's near them; Explorers buy eyes |
| NanoAI ("if it dies you can't build") | the unit carrying your code — a treatment that runs out of hands |
| 1500 turns | the window before the compound denatures |
| 50 ms budget | how long the swarm can wait for orders before the moment has passed |
| Two players | rival candidate protocols; only one gets used on a real patient |

It closes on the purpose angle for a young audience: underneath the
tissue this is autonomous-agent programming — route-finding under real
costs, resource logistics, risk assessment, all inside a hard time
budget. *"The tissue is imaginary. The skills are not."*

## Changed — the story now leads everywhere

- **Landing page**: new hero ("They're too small to pilot. So you write
  their mind.") plus a **Briefing** section — six cards, each showing a
  rule *as something the body or your rival is actually doing* — and a
  nav entry.
- **Participant guide**: §1 opens with a one-paragraph mission callout
  before the mechanical description.
- **Tutorial** and **README**: short in-fiction hooks that link to the
  full briefing.

## Verification

```
$ pytest tests/  -> 362 passed
HTML tag-balance clean (index.html, participant_guide.html);
briefing section + nav link present; no stray markup.
Checked: the original inspiration is never named anywhere.
```
