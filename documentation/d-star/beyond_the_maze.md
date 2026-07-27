# D* Lite Beyond the Maze: Stress-Testing the Abstraction

## Purpose

`environment_changes.md` and `agent_changes.md` design a toy example: a grid maze with one bridge that can break and be fixed, small enough to reason about by hand and to visualize with the existing dashboard tooling. Before treating that design as settled, it's worth checking whether the abstraction actually generalizes — or whether it only works because a maze is a uniquely forgiving shape (small, single-agent, single-path, geometric heuristic available for free).

This document maps the same design onto a real, larger dynamic graph — a multi-repo GitHub CI/CD pipeline — and records where the mapping holds and where it strains. It is **not** a build spec. Nothing here is scheduled for implementation; it's a cross-check on the model, kept separate so it doesn't dilute the maze docs with a system that's a different order of complexity.

## The Mapping

| Maze concept | CI/CD pipeline concept |
|---|---|
| Node `(r, c)` | A repo/commit/deploy-context state, e.g. `repo_A:head_sha`, `main:merge_sha`, `staging_deploy:context` |
| Edge | A workflow dependency or `repository_dispatch` trigger between two states |
| Edge cost `1` | A check passes / normal execution latency |
| Edge cost `∞` (broken bridge) | A CI check fails, a review thread is unresolved, or a downstream deploy context (e.g. `manta-deploy/staging`) fails |
| Bridge break / fix | A check flips from passing to failing, or back |
| **Driver** (the external actor calling `break_edge()`/`fix_edge()`) | You, working through an OpenCode session: merging PRs, pushing fixes, triggering re-runs |
| `drain_changed_edges()` | Polling `gh run list --commit {sha}`, `gh api repos/.../commits/{sha}/statuses`, PR comment/review state |
| Goal node | A target release or deploy state |
| `g(s)` / `rhs(s)` | Same meaning as in `d_star_lite.md` — cost-to-goal from a given pipeline state, and its one-step-lookahead estimate from successor states |

This table is the whole exercise: everything below is either confirming a row holds up under scrutiny, or explaining why it doesn't.

## Where the mapping holds

- **The Driver/Agent separation is intact.** `agent_changes.md`'s sequence diagram already has an external "Driver" calling `env.break_edge()` between the agent's moves, with the agent doing nothing but sensing and replanning. Mapped onto GitHub, you (via OpenCode) are that Driver — merging PRs and pushing fixes is what changes edge costs; the D* Lite agent only ever polls and repairs its plan. This was the point raised and resolved earlier in the investigation: the agent does **not** act on the world itself, which keeps this a legitimate D* Lite application rather than an action-conditioned planning problem wearing D* Lite's vocabulary.
- **The incremental-repair value proposition is real, not just decorative.** One downstream check flipping (say, `manta-deploy/staging` failing) shouldn't require re-evaluating the entire multi-repo dependency graph — exactly the property D* Lite is for. The bigger and more expensive the graph, the more this matters; a CI/CD graph across several repos is a case where the payoff of "only touch the locally affected sub-graph" is larger than in a small teaching maze, not smaller.
- **The environment property classification carries over unchanged.** Using the same vocabulary as `environment_changes.md`'s property table: dynamic (not static — checks change state continuously), known (the graph's topology — which repos depend on which — is not hidden, only *when* a check will flip is unknown), sequential (past state affects what "changed" means), discrete (finite set of pipeline states). Nothing about moving from a maze to a pipeline forces a different property profile.

## Where it strains

- **No natural admissible heuristic.** Manhattan distance is cheap, obviously admissible, and consistent for a grid — it's what makes A*/D* Lite's heuristic-guided search meaningfully better than plain Dijkstra in the maze. The closest analogue over a CI/CD DAG is topological distance (how many pipeline stages remain), but that's approximately what you get from unweighted graph distance anyway — it doesn't encode anything about *which* remaining stages are likely to be slow or likely to fail. In practice this means the heuristic-guided part of D* Lite's advantage over an undirected incremental-Dijkstra-style repair is largely cosmetic here. The incremental-repair mechanism (§ above) still earns its keep; the heuristic doesn't add much on top of it in this domain.
- **Concurrency mismatch.** D* Lite's entire formulation assumes a single agent occupying a single node, moving to one adjacent node at a time. A real CI/CD pipeline fans out (multiple checks run in parallel on one commit) and fans in (multiple upstream repos gate one downstream deploy) — there isn't one "current position" to compute `rhs` relative to. Mapping this cleanly requires either (a) picking one critical path through the graph at a time and treating everything off that path as out of scope for a given planning run, or (b) accepting that the real problem is closer to dependency-DAG scheduling with failure recovery than to single-agent pathfinding, and that D* Lite is only directly applicable to the "which sequence of gates must I get through to ship this one change" slice of it, not the whole multi-lane graph at once.
- **Escalation is a boundary, not a resolution.** The natural D* Lite condition for "no path exists" is `g(s_start) == ∞` — every successor has infinite cost, meaning every route to the goal is currently blocked. Mapped onto CI/CD, that's the right trigger for an alert (tag a human, post a failure summary), but it's worth being explicit that this is where the algorithm's job ends. D* Lite doesn't have an opinion about *how* a blocked edge gets un-blocked — in the maze that's outside the agent entirely (the Driver fixes the bridge); in the CI/CD mapping it's the same thing, except the Driver is a person (or another agent instance) deciding whether and how to fix a failing check. The algorithm tells you precisely which edge is the blocker and that everything downstream of it is currently unreachable — it does not, and structurally cannot, decide what fixing that edge looks like.

## Open questions (explicitly undecided)

- Does this mapping get built at all, or does it stay a conceptual cross-check that informed the maze design and stops there?
- If it does get built: scoped to one critical-path slice of a real pipeline (single PR → merge → deploy chain), or the full multi-repo, multi-lane graph? The concurrency mismatch above suggests the former is the only version that stays faithful to D* Lite rather than becoming a different algorithm.
- Is the Driver (you, via OpenCode) ever modeled as a percept source inside the system, or does it stay entirely external — an actor the documentation acknowledges but the implementation never represents?

## Relationship to the maze work

This document exists to pressure-test the design, not to extend its scope. The maze in `maze_solver/`, as designed in `environment_changes.md` and `agent_changes.md`, remains the actual teaching deliverable — nothing here is a prerequisite for it, and nothing here should be read as the "real" version the maze is a simplified stand-in for. It's the reverse: the maze is deliberately the version worth building first *because* it doesn't have the two problems identified above (it has a clean heuristic, and one agent genuinely does occupy one cell at a time).
