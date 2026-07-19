# The Trials

## You will never see them work.

The bots you are about to program are smaller than a red blood cell.
The entire operation — injection to extraction — lasts about as long as
a held breath. By the time a signal from your hand reached them, it
would already be over.

So you don't drive them.

You write the mind they carry in with them, and then you let go.

---

## The patient

Somewhere past the skin, a treatment is failing.

The compound that would fix it — **AZN** — can't simply be injected into
the blood. Delivered at large, it breaks down long before it reaches the
tissue that needs it. It has to be carried, molecule by molecule,
to specific **receptor sites** buried deep in the body, and held there
by a delivery implant while it does its work.

That is the whole job. Find the sites. Carry the medicine. Hold on.

A **NanoNeedle** anchored on a receptor site is doing something the
moment it lands — but an empty needle is barely treatment at all. Feed
it, and the dose it delivers climbs sharply. The best protocols don't
just plant needles. They keep them fed.

---

## The body does not know you are helping

This is the part every new team underestimates.

The immune system has no idea what you are. To a white blood cell, a
nanobot is a foreign body the size of a bacterium, moving with purpose
through tissue it is sworn to defend. It does what it has always done.

It is not malice. It is the patient's own body, working correctly,
trying to save a life — and your swarm is in the way.

You can route around the patrols. You can wall them out. You can, if you
must, put a collector's emitter on one and burn it down; they do not
come back. Every team decides for itself how much of the treatment
window it is willing to spend fighting the patient it came to save.

---

## The terrain is alive

Nothing here is a level designed for you.

**Tissue** varies. Loose tissue is quick to cross; dense tissue drags at
you. **Bone** doesn't negotiate — you go around.

**Bloodstreams** run one way, and they run fast. Ride one and you'll
cross the body in a fraction of the time. Enter against the current and
you'll wish you hadn't. Committing to the flow is a real decision:
it's the fastest road in the body and you can't turn around on it.

And you cannot see very far. Your bots sense only what's near them.
Somewhere out there is another team's swarm and you will not know where
until something of yours stops reporting — unless you spend the mass on
an **Explorer** and buy yourself eyes.

---

## Why there are two of you

Only one protocol gets to run in a real patient.

So the candidates are run head to head, in the same simulated body, on
the same failing tissue, against the same clock. Two swarms, one set of
receptor sites, one supply of AZN. Whichever protocol holds more of the
patient stable when the window closes is the one that gets used.

Your rival is not a monster. It's another team's code, written by people
exactly as clever as you, and it wants the same sites you do.

---

## The window

You get **1500 turns**. That's the whole treatment window — after that
the compound denatures and the operation is over, finished or not.

Every turn, each of your bots may do exactly one thing. Move. Collect.
Deliver. Build. Defend. One.

And your code has **50 milliseconds** to decide all of it. That isn't an
arbitrary rule either — it's how long the swarm can wait for orders
before the moment it was asking about has passed. Take longer and the
turn is simply gone, and your bots stand there in someone's bloodstream
doing nothing.

---

## What you're actually learning

Here is the part nobody tells you at the start.

Underneath the tissue and the patrols, this is one of the hardest and
most useful problems in computer science: **getting autonomous agents to
do the right thing when you aren't there to tell them.**

You will end up doing route-finding under real movement costs, because
straight-line distance lies. You'll do resource logistics, because a
collector walking an extra fifteen turns each trip is a dose that never
arrives. You'll do risk assessment, because expanding to a second site
you can't defend is how good teams lose. And you'll do all of it inside
a hard time budget, which is the constraint every real robotics system
lives under.

This is the same shape of problem as a warehouse full of robots, a
search-and-rescue drone team, or — yes — an actual medical microswarm.
The tissue is imaginary. The skills are not.

---

## Your first swarm

You start with one bot: the **NanoAI**. It carries your code, and it is
the only thing in the body that can build the rest. Everything your
swarm ever becomes gets built by it, out of the AZN you collect.

Protect it. If it goes down, your swarm keeps whatever it had and can
never build again — a treatment that slowly runs out of hands.

Then decide what kind of team you are.

Some teams turtle: one site, fed to the brim, walled and watched, and
they dare you to come take it. Some run wide and greedy, two sites,
three collectors, out-scoring you faster than you can hurt them. Some go
hunting, and try to make sure nobody's protocol finishes but theirs.

Every one of those has beaten the others. None of them wins every time.

The window is open. Write something good.

---

*New here? [`TUTORIAL.md`](TUTORIAL.md) gets you from one needle to a
strategy that survives an attacker, in four runnable stages.
[`STRATEGY_API.md`](STRATEGY_API.md) is the complete API on one page.*
