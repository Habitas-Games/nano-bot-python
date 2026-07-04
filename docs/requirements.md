# nano-bot — Requirements & Roadmap

**Revision:** 2 (supersedes the original port-era requirements)
**Status legend:** ✅ implemented · 🟡 partial · ⬜ planned · ❓ needs a design decision

## 1. Overview

nano-bot is a turn-based AI programming competition set inside a
simulated human body. Participants write a Python strategy file that
commands a fleet of nanobots across a grid of living tissue: collecting
AZN (the energy molecule), claiming **Habitas Points**, and outscoring
an opponent over up to 1500 turns. The platform includes a headless
simulation engine, a visual match/replay window, a round-robin
tournament runner, and a visual map editor.

The product vision is a competition that is **fun to play and fun to
watch**: strategies should win through map reading, economy, timing,
and risk-taking — not by exploiting a dominant mechanic — and a
spectator should be able to follow the story of a match from the replay
alone.

## 2. Goals

| # | Goal | Status |
|---|---|---|
| G1 | Participants submit a single Python strategy file — no engine knowledge required. | ✅ |
| G2 | Two or more strategies battle simultaneously on the same map. | ✅ (2 via UI, up to 4 via CLI) |
| G3 | The simulation runs headlessly for fast batch evaluation. | ✅ |
| G4 | A visual match window lets anyone watch a replay step by step — and re-run with different maps/strategies without leaving it. | ✅ |
| G5 | Tournament mode ranks all submitted strategies on a leaderboard. | ✅ |
| G6 | Every bot type and mechanic is genuinely useful somewhere — no dead stats, no strictly-dominant strategy. | 🟡 (see §9) |

## 3. Scope

**In scope:** grid map engine (density, bloodstreams, bone), 8 nanobot
types, turn-based simulation ≤1500 turns, Python strategy API, 2D
visual playback with match setup, scoring, round-robin tournaments,
JSON match/map formats, visual map editor.

**Out of scope:** 3D visualization, networked multiplayer, a strategy
IDE, full script sandboxing (strategy authors are trusted — a strategy
is imported as ordinary Python), mobile/web export.

## 4. Functional Requirements

### 4.1 Map System

| ID | Requirement | Status |
|---|---|---|
| MAP-01 | The map is a 2D grid. Each map JSON declares its own width/height (shipped maps: 80×80 and 60×60; recommended max 200×200). Non-positive dimensions are rejected at load. | ✅ |
| MAP-02 | Each cell has a tissue **density**: Low (move cost 2), Medium (3), High (4), or Bone (impassable). | ✅ |
| MAP-03 | Cells may carry a directional **bloodstream** (N/S/E/W). Moving with the stream: −2 cost; against: +2; minimum cost always 1. | ✅ |
| MAP-04 | Maps are external JSON files; new maps require no engine changes. | ✅ |
| MAP-05 | Maps declare **Habitas Points** (scoring objectives), **AZN nodes** (position + finite quantity), and a per-map **starting AZN budget**. | ✅ |
| MAP-06 | Maps declare one rectangular **injection zone per player**. A player spawns inside their zone; if the requested or default cell is impassable, the engine picks a random passable cell in the zone (seeded RNG — reproducible). | ✅ |
| MAP-07 | The platform ships with at least **3 pre-built maps** of distinct character (e.g. open tissue, stream highways, bone maze). | 🟡 (2 shipped) |
| MAP-08 | The map editor can author everything a map JSON can express — including which player owns an injection zone. | 🟡 (new zones are always player 1; no owner selector) |

### 4.2 Nanobot Types

Stats live in `data/bot_types.json` (NFR-02). All 8 types are
implemented and verified by example strategies that exercise them.

| ID | Type | Requirement | Status |
|---|---|---|---|
| BOT-01 | **NanoAI** | One per player, spawns free, cannot be rebuilt. HP 20, Scan 5. The only bot that can `build()`. If it dies, that player can issue no further actions (in-flight movement completes). | ✅ |
| BOT-02 | **NanoExplorer** | 15 AZN. HP 20, Scan 30. Ignores density cost (pays minimum move cost; Bone still impassable; streams still apply). | ✅ |
| BOT-03 | **NanoCollector** | 20 AZN. HP 50, capacity 20, transfer 5/turn. The only attacker: damage 1–5, range 12 (Euclidean). | ✅ |
| BOT-04 | **NanoContainer** | 25 AZN. HP 60, capacity 60, transfer 5/turn. Cannot attack. Can receive and relay AZN (collector → container → needle). | ✅ |
| BOT-05 | **NanoNeedle** | 40 AZN. HP 150, capacity 100. Stationary once built. Placed on a Habitas Point it scores per §4.5. | ✅ |
| BOT-06 | **NanoIPCreator** | 30 AZN. HP 20, Scan 30. `open_ip()` registers its current cell as a **permanent new injection point** for its owner (bank AZN there). Auto-destructs after 500 turns; the point survives it. | ✅ |
| BOT-07 | **NanoBlocker** | 20 AZN. HP 90. Enemy bots crossing its cell pay +6 turns (density-immune bots exempt). | ✅ |
| BOT-08 | **NanoWall** | 25 AZN. HP 100. Impassable to enemies. Auto-destructs after 50 turns. | ✅ |
| BOT-09 | Players start with only their NanoAI; everything else is built at Manhattan-distance 1 from it, on a passable cell, paying the type's cost from the bank. | ✅ |
| BOT-10 | Transfers can target **any friendly bot with storage capacity** (needle or container), or the player's bank when standing in one of their injection zones. Rate-limited per the giver's transfer stat; capped by the receiver's free capacity. | ✅ |

### 4.3 Strategy API

| ID | Requirement | Status |
|---|---|---|
| STR-01 | A strategy is one `.py` file defining exactly one `NanoStrategy` subclass. Multiple candidate classes in one file fail loudly at load (no silent guessing). | ✅ |
| STR-02 | Exactly two overrides: `choose_injection_point(map_info)` (once, pre-match) and `what_to_do_next(map_info, my_bots)` (once per turn). | ✅ |
| STR-03 | `map_info` exposes read-only: cell grid (`get_cell`), habitas points, AZN nodes, visible enemies, turn number, own bank. *Currently all enemies are always visible — see GAME-01.* | 🟡 |
| STR-04 | `my_bots` is a list of `BotProxy` objects: type, position `(x, y)` tuple, hp/max_hp, azn, is_alive/is_moving/has_path, plus action methods (`move_to`, `collect_from`, `transfer_to`, `defend`, `build`, `open_ip`, `stop`, `self_destruct`). Last queued action per bot per turn wins. | ✅ |
| STR-05 | `what_to_do_next` has a **50 ms** wall-clock budget; exceeding it (or raising) forfeits that turn with a logged warning — it never crashes the match. | ✅ |
| STR-06 | Strategies load from `strategies/`; any `.py` file there is a candidate. Load errors mark the entry DQ in tournaments rather than crashing. | ✅ |
| STR-07 | The shipped example strategies form a learning path: a minimal scorer, a full economic loop, one focused demo per remaining mechanic (explorer, container relay, defense, combat, injection points), and one all-mechanics strategy. **Every shipped strategy scores points in normal play** (only losing its needle to combat can zero it). | ✅ |

### 4.4 Simulation Engine

| ID | Requirement | Status |
|---|---|---|
| SIM-01 | A match runs at most **1500 turns**. | ✅ |
| SIM-02 | Per-turn phase order: (1) timers tick, (2) movement advances, (3) strategies are called, (4) queued actions execute, (5) attacks resolve, (6) auto-destructs fire, (7) NanoAI deaths are registered, (8) scores recomputed from live state. | ✅ |
| SIM-03 | Pathfinding is cost-aware A* over directed edges (density + stream modifiers, and the mover's density immunity), not hop-count. | ✅ |
| SIM-04 | Attack range uses Euclidean distance; damage is `randint(1, max_damage)` from the match RNG. | ✅ |
| SIM-05 | Headless mode completes a 1500-turn match on shipped maps in well under 5 s. | ✅ (~0.1 s typical) |
| SIM-06/07 | Every turn's full state is recorded and exported as a JSON replay (`replays/*.json`). | ✅ |
| SIM-08 | 2–4 players per match. UI runs 1v1; the headless CLI accepts up to 4 (`--strategy_a..d`). | 🟡 |
| SIM-09 | The match ends at turn 1500 or as soon as at most one player has living bots. | ✅ |

### 4.5 Scoring

| ID | Requirement | Status |
|---|---|---|
| SCO-01 | Needle on a Habitas Point with 0 AZN: **5 pts/turn-recomputed**. | ✅ |
| SCO-02 | Needle with AZN: **20 + 2 × AZN stored**. Scores are recomputed from live state every turn — a destroyed needle's contribution vanishes immediately. | ✅ |
| SCO-03 | Optional per-map bonus objectives (e.g. +50 for holding all points). | ⬜ (never implemented; keep or drop with M6) |
| SCO-04 | Highest score at match end wins. Ties break by: (1) bots alive, (2) AZN banked, (3) lowest player number. ("Turns elapsed" was dropped — it is not a per-player value and can never discriminate.) | ✅ |
| SCO-05 | Final and per-turn scores are in the replay JSON. | ✅ |

### 4.6 Visual Match Window & Playback

| ID | Requirement | Status |
|---|---|---|
| VIS-01 | The match window renders a replay as an animated 2D top-down scene using the real tile/marker/bot art (same assets as the map editor). | ✅ |
| VIS-02 | Terrain uses tissue textures; bloodstream cells show the stream texture plus a directional arrow overlay. | ✅ |
| VIS-03 | Bots show their type sprite inside a team-colored ring; the default zoom keeps sprites recognizable. | ✅ |
| VIS-04 | Controls: play/pause, step ±1, speed 0.25×–4×, and a **jump-to-turn slider**. Zoom via wheel; pan via left-drag (click-without-drag selects a bot) or middle-drag. | ✅ |
| VIS-05 | HUD: map name, turn counter, per-player score + bots alive (labels are 1-indexed: "Player 1"/"Player 2"), winner line, map legend, and an always-visible bot inspector. | ✅ |
| VIS-06 | Habitas Points render neutral (gold) or tinted with the owning team's color; stored AZN is labeled. | ✅ |
| VIS-07 | **Match setup lives in the match window**: Map / Player 1 / Player 2 pickers plus a Restart button re-simulate in place on a background thread. The main menu is a plain launcher. | ✅ |
| VIS-08 | Event effects (attack, build, collect, destruct) render as brief animations so a spectator can see *why* the state changed. | ⬜ (UX-03) |

### 4.7 Tournament Mode

| ID | Requirement | Status |
|---|---|---|
| TRN-01 | Round-robin: every strategy vs every other, on every shipped map. | ✅ |
| TRN-02/03 | Results accumulate into a leaderboard (W/L/D, points), shown in-app and exported to `tournament_results.json`; every match's replay is saved. | ✅ |
| TRN-04 | DQ'd strategies (load error, timeout) appear on the leaderboard as DQ, never silently skipped. One failed match cannot kill the run. | ✅ |
| TRN-05 | A dedicated summary view highlights the top finishers. | 🟡 (full ranked list shown; no distinct top-3 view) |

## 5. Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-01 | Headless 1500-turn match ≤5 s on typical hardware. | ✅ |
| NFR-02 | Bot stats, maps, and (future) hazards are data files — no engine edits to tune them. | ✅ |
| NFR-03 | Runs anywhere Python 3.10+ and pygame run (Linux/Windows/macOS); `run.sh` bootstraps a venv. | ✅ |
| NFR-04 | A strategy error can never crash a match or tournament; it costs that player the turn (or a DQ) and is logged. | ✅ |
| NFR-05 | Same map + strategies + seed ⇒ identical match, including random spawn fallback and damage rolls. | ✅ |
| NFR-06 | A participant with basic Python can go from `cp example_strategy.py` to watching their own match in under 30 minutes using only the guide. | ✅ |

## 6. Gameplay & UX Review Findings (this revision)

Reviewed as a game, not just a port. What already works: the economy
loop (collect → deliver → score) is legible and rewarding; the match
window makes iteration fast (pick, restart, scrub); the art reads as a
place, not a grid; the 8 example strategies teach every mechanic.

What holds the fun back, in priority order:

1. **Nothing in the body fights back.** The theme promises a hostile
   immune system; today the only danger is the other player. Most
   matches are two parallel economies that barely interact. (→ GAME-02)
2. **Scan is a dead stat, scouting a dead role.** All enemies are
   always visible, so NanoExplorer's Scan 30 and the recon phase of a
   match don't exist. Hidden information is the cheapest source of
   drama and differing strategies. (→ GAME-01)
3. **Combat is a coin with one side.** A single attacking collector
   shuts out any economic strategy 14–0; walls/blockers stop movement
   but not ranged attacks, so there is no counterplay. Attackers should
   win fights, not delete the genre of non-fighting strategies. (→ GAME-03)
4. **Contested Habitas Points resolve silently and unfairly** — the
   later-built needle takes 100% of the score. (→ GAME-04)
5. **Watchability**: state changes (attacks, builds, deaths) happen with
   no visual event, and GUI matches always run seed 0, so a rematch
   with the same setup is move-for-move identical. (→ VIS-08, UX-04)

## 7. Roadmap Requirements (M6 "Make it a game", M7 "Polish")

| ID | Requirement | Status |
|---|---|---|
| GAME-01 | **Fog of war.** `visible_enemies` contains only enemies within any friendly bot's Scan radius (Euclidean). Habitas/AZN positions stay global (they're on the map); enemy *bots* must be scouted. Replay stores ground truth; the viewer may show all. | ⬜ |
| GAME-02 | **Immune-system hazards.** Maps may declare patrolling white-cell hazards (path or radius, HP, contact damage). They attack the nearest bot in range of either player; collectors can fight them; walls block them; blockers slow them. Data-driven per NFR-02. | ⬜ |
| GAME-03 | **Combat counterplay.** Proposed rule: attacks require line of sight — Bone and alive NanoWalls on the segment block the shot. Acceptance: a needle ringed by walls survives a lone attacker until the walls expire; walls become a real defense with a real upkeep cost. | ❓ decide rule before implementing |
| GAME-04 | **Habitas exclusivity.** `build("NanoNeedle", p)` fails (logged event) if an alive enemy needle already occupies point `p`. First claim holds until the needle dies. | ❓ confirm rule |
| GAME-05 | **Third shipped map** with a distinct archetype (bone maze or stream-highway), authored in the map editor. Satisfies MAP-07. | ⬜ |
| UX-01 | **Replay browser**: open any `replays/*.json` (tournament and headless runs included) from the match window. | ⬜ |
| UX-02 | **Zone owner selector** in the map editor (completes MAP-08). | ⬜ |
| UX-03 | **Event VFX + menu art**: brief effect animations for attack/build/collect/destruct (VIS-08) and the existing menu background/logo art wired into the main menu. | ⬜ |
| UX-04 | **Seed control**: Restart uses a new random seed by default, with the seed shown and re-enterable for exact reruns (GUI currently hardcodes seed 0). | ⬜ |

## 8. Milestones

| Milestone | Status |
|---|---|
| M1 Core engine · M2 Strategy API · M3 Playback · M4 Tournament · M5 Map editor | ✅ Done (see `docs/versioning/`) |
| M6 **Make it a game** — GAME-01..05 (fog of war, hazards, combat counterplay, habitas exclusivity, third map) | ⬜ Next |
| M7 **Polish & spectate** — UX-01..04, TRN-05 summary view, SCO-03 decision | ⬜ |
