# Related Algorithms to Explore

## Purpose

This is a backlog, not a plan: a scoped menu of algorithms adjacent to D* Lite, surfaced while designing the maze toy example, with a note on why each might be worth a follow-on toy example and roughly what order makes sense. Nothing here is committed — it exists so the next "what should we look at" conversation starts from a written list instead of memory.

## Same family: incremental / replanning search

| Algorithm | Relationship to D* Lite | Why it's worth building | Suggested order |
|---|---|---|---|
| **LPA\* (Lifelong Planning A\*)** | D* Lite's foundation, with the moving-agent complexity removed: fixed start and goal, only the graph changes | Isolates the repair mechanism (`g`/`rhs`/`UpdateVertex`) from the movement loop. Build this on the *same* bridge-break maze, but with the agent standing still — "the graph changed, patch the plan" without "and also I moved." Cleaner staircase into D* Lite than starting with D* Lite itself | Before or alongside D* Lite — see [`d_star_lite.md`](../../search_algorithms/d_star_lite.md)'s "Relationship to LPA\*" section, which already frames D* Lite as "LPA* run backward + a `km` term for a moving start" |
| **D\* Lite** | — | Already designed: [`d_star_lite.md`](../../search_algorithms/d_star_lite.md), [`environment_changes.md`](environment_changes.md), [`agent_changes.md`](agent_changes.md) | Current focus |
| **Anytime D\* (AD\*)** | Layers anytime search (return a suboptimal-but-valid plan fast, keep improving it) on top of D* Lite's incremental repair | Real-world pedigree — this is what ran in DARPA's Urban Challenge vehicles. Interesting if the cost-of-waiting-for-optimality tradeoff is worth demonstrating on top of the repair mechanism | After D* Lite, only if the anytime/quality tradeoff is the next thing worth teaching |
| **Original D\* / Focused D\*** (Stentz, 1994) | D* Lite's historical predecessor | Context, not a build — D* Lite supersedes it for teaching purposes. Worth a paragraph of history, not its own implementation | Not planned as a separate doc |

## Adjacent thread: closing the "is this like Q-learning?" question

Raised earlier in this investigation — D* Lite's `rhs(s) = min(cost(s,s') + g(s'))` is a Bellman equation, and updating only the states whose value actually changed resembles prioritized sweeping / real-time dynamic programming in RL, but D* Lite is exact incremental *planning* over known costs, not learning from reward samples. These two algorithms are where that resemblance stops being an analogy and becomes something concretely buildable:

| Algorithm | What it demonstrates | Why it matters |
|---|---|---|
| **LRTA\* (Learning Real-Time A\*, Korf 1990)** | An agent that moves in real time with *bounded lookahead*, and updates its heuristic estimates from experience each time it acts — repeated trials make the heuristic (and therefore the path) progressively better | A genuine bridge between classical search and RL: local Bellman-style value propagation, but "learning" here means heuristic improvement over repeated episodes, not a reward-driven policy. Building this would give a concrete, working answer to the Q-learning question instead of a written explanation. Also the correct algorithmic home for the "Atomic Action Pair" (guarded LLM generator + retry budget) primitive — see [`documentation/lrta/beyond_the_maze.md`](../lrta/beyond_the_maze.md), which stress-tests that mapping against real `gh` CLI effectors |
| **RTAA\*** | A refinement of LRTA* that updates a batch of heuristic values per move instead of one | Same pedagogical payoff as LRTA*, more practical performance — worth mentioning alongside it rather than as a separate build |

## Surfaced by the real-world stress test: AND-branching

None of the algorithms above handle this — it wasn't apparent from the maze at all, only from checking the LRTA* mapping against `atomicguard`'s real guard-graph workflows:

| Algorithm | What it demonstrates | Why it matters |
|---|---|---|
| **AO\* (AND-OR graph search)** | Distinguishes OR-nodes (pick the cheapest of several alternative branches — what D* Lite/A*/LRTA* all assume) from AND-nodes (every branch must resolve before the node is satisfied) | [`documentation/lrta/beyond_the_maze.md`](../lrta/beyond_the_maze.md) found a real fan-in case (`post_merge_monitor.dspddl`'s `downstream-ci-passed`, which requires three independent deploy contexts to *all* succeed) that none of D* Lite, LPA*, or LRTA* can represent without distortion — their value-update rules are all `min`-over-successors (OR-composition), and this needs a `max`-over-required-predecessors (AND-composition). AO* is the classical algorithm built for exactly that distinction. Worth a toy example specifically because the maze, being a single corridor-following agent, never produces an AND-node naturally — you'd have to construct one on purpose (e.g. "both the north bridge and the south bridge must be intact to proceed") to demonstrate the gap at all. This is exactly why [`documentation/task-graph/`](../task-graph/) exists — a new toy environment, generalized beyond GitHub to any `atomicguard`-shaped guard-graph (disk checks, package repair, cert checks, PR merges), built around AND-`requires` edges natively rather than approximating them on a grid |

## Unrelated to the dynamic-environment thread, already flagged as gaps

`search_algorithms/README.md`'s existing "Other Search Algorithms (not yet implemented)" section already lists: Uniform-Cost Search, Iterative Deepening Search, Depth-Limited Search, Bidirectional Search, Beam Search, Jump Point Search. These are static/classical algorithms with no connection to the dynamic-replanning thread this document is tracking — listed here only so this doc doesn't duplicate or contradict that one. They'd round out the base `maze_solver` algorithm suite if that ever becomes a separate goal.

## Suggested sequencing, if this backlog gets picked up

1. **LPA\*** — de-risks D* Lite by separating "the graph changed" from "and I also moved," on infrastructure that's almost entirely shared with the D* Lite design already written.
2. **D\* Lite** — the current toy example; design docs done, implementation not started.
3. **LRTA\*** — a distinct teaching thread that directly resolves the Q-learning comparison with working code rather than an explanation.
4. **Anytime D\* / RTAA\*** — deeper follow-ons, only worth scoping if 1–3 land and there's appetite for more.

## Not decided

- Whether any of these get built at all — this is a menu, not a roadmap with dates.
- Whether LPA* is worth its own environment/agent design docs (mirroring D* Lite's), or is small enough to fold into `d_star_lite.md` as a "build this subset first" section instead of a parallel doc set.
- ~~Whether LRTA*/RTAA* belong under `documentation/d-star/` at all~~ — resolved: [`documentation/lrta/`](../lrta/) now exists, holding [`beyond_the_maze.md`](../lrta/beyond_the_maze.md). Still open: whether LRTA* gets the same environment/agent design-doc split D* Lite got, or whether the stress-test doc is enough on its own for now.
