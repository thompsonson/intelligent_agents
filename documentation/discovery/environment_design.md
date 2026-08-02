# Discovery: Environment Design (Step 1)

## Purpose

Every environment built so far — `maze_solver/`'s grid, `task_graph_solver/`'s and `path_maintenance/`'s DAGs — hands the agent a fully-specified topology up front. Search means finding a route through something already visible; maintenance means keeping a committed-to path healthy. Both assume **Known**: the graph exists, in full, before the agent takes a single step.

This document drops that assumption. The agent doesn't know what comes after the node it's standing on until it asks that node directly — and it can't ask about a node it hasn't heard named yet. Knowledge of the graph is built incrementally, one query at a time, starting from nothing but a start id.

This is a new environment, not an extension of `path_maintenance/`'s. It shares no code with `PathGraphEnvironment`/`JobGraphEnvironment` — the direction of the edge itself is different (see below), and there is deliberately no `ready_nodes()`-equivalent, because "the frontier of what's ready" presupposes a global view of the graph that this environment specifically withholds.

## The edge points the other way

`GraphNode`/`JobNode`'s `requires` is pull-direction: a node declares its own prerequisites, and the environment can answer "what does X depend on" for any X, any time, because the whole `requires` graph is given at construction.

A real CI pipeline doesn't work that way from the point of view of something walking it. Pipeline `A` doesn't know who depends on it — it just knows who it *notifies* when it finishes, because that's configured in `A`'s own file. Finding out that `B` comes after `A` means reading `A`'s config, not `B`'s. That's push-direction, and it's node-local: you learn it by querying the node you're at, not by consulting a global map.

`DiscoveryNode` carries `notifies` — the same shape as `requires`, direction reversed, and (for this step) that's the *only* edge field. `requires`-style AND-gating is deferred (see below); a node here has successors, not prerequisites.

## Environment properties

| Property | Value | Why |
|---|---|---|
| **Known/Unknown** | **Unknown** | This is the property every other environment in this repo holds fixed at Known. The graph exists (the environment holds it in full — see below), but the agent has no access to it except by querying nodes it has already reached |
| **Observable** | **Partially** | The agent can query any node id it already knows about — but it only ever learns a new id by seeing it named in an already-queried node's `notifies`. There's no enumeration, no "list all nodes." Contrast with `path_maintenance/`'s "fully, but lazily" — there, everything is *reachable* by query even if the agent chooses not to; here, most of the graph isn't reachable by query at all until something else has been queried first |
| **Static/Dynamic** | Static | Confirmed for this step: a node's `notifies`, once sensed, doesn't change later. (A real pipeline gaining new notifications after it runs — e.g. a deploy spinning up more pods — is real, and deliberately deferred, not modeled here) |
| **Single/Multi-agent** | Single-agent | No other agent mutates state in this step — that framing belongs to `job-lifecycle/`, not here |
| **Deterministic/Stochastic** | Deterministic | `sense_edges(node_id)` always returns the same `notifies` for a given id |
| **Episodic/Sequential** | Sequential | Which node to visit next depends on accumulated history — the set of ids already known and already visited — not just the current node in isolation |
| **Discrete** | Yes | Finite node set, finite edges, unit move cost |

## Resolved design questions

A handful of forks came up while settling this shape; recorded here rather than left implicit, the same way `job-lifecycle/environment_design.md` records its own resolved gaps.

**Arrival gates *querying*, but the environment doesn't enforce it.** The agent's own discipline is to only call `sense_edges` on the node it currently considers itself at — that's the whole discovery premise, learning edges by being there rather than by lookup. But the environment itself tracks no position (next point) and therefore has no way to check "did you actually arrive" even if it wanted to. `sense_edges(node_id)` raises only if `node_id` isn't a real node anywhere in the graph — the same "unknown id" `ValueError` every prior environment already raises — never for "you haven't earned the right to ask this yet." Nothing about this environment stops an agent from calling `sense_edges` on an id it merely knows about but hasn't visited; it just wouldn't be doing discovery correctly if it did, the same way nothing stops a `path_maintenance/` agent from deviating from its computed `order`, and it simply isn't asked to.

**Environment tracks no position; the agent owns both its start point and its current position.** Every prior environment (`MazeEnvironment`, `PathGraphEnvironment`, `JobGraphEnvironment`) leaves position-tracking to the agent, and there's no discovery-specific reason to break that convention — "the environment returns whatever node the agent asks for" is the whole contract, nothing more. `DiscoveryEnvironment` has no `start_id`, no `current`, no `move_to()`. The agent is constructed with a `start_id` and updates its own bookkeeping as it moves.

**Movement is constrained to the current node's already-sensed `notifies`, self-enforced by the agent.** Confirmed: no teleporting to a known-but-unvisited id from somewhere else. Since the environment doesn't track position, it can't enforce this either — it's a rule the agent's own traversal logic follows, not something `DiscoveryEnvironment` can reject.

**`requires` (AND-joins) deferred to a later step.** A node arriving with unsatisfied prerequisites — and detouring to satisfy them as a first action, backward-chaining style — is real and worth building, but it's a second mechanism layered on top of forward discovery, not part of it. Preserved for that later step: *"when an agent arrives it checks all requires are satisfied, moving to any that are not satisfied as a first action."*

**Goal: a node with no `notifies`.** Rather than a named target known in advance, the goal is structurally discovered — a terminal the agent finds by walking into it. Caveat worth keeping visible: "no `notifies`" alone doesn't distinguish *the* goal from an incidental dead end if a scenario happens to have more than one such terminal. `scenario.md` needs exactly one reachable terminal for this step, to keep the goal condition unambiguous without needing extra machinery to pick among terminals.

**Cost: flat 1, not zero.** Chosen over "no cost" so the concept exists to be varied later, without anything in this step actually depending on the number — same precedent as `MazeEnvironment.get_step_cost()`, which has returned a flat 1 since before any algorithm in this repo needed weighted costs.

## Proposed API surface (signatures only — no implementation yet)

```python
@dataclass(frozen=True)
class DiscoveryNode:
    id: str
    notifies: Tuple[str, ...] = ()
    # no `requires` yet - AND-joins deferred, see "Resolved" above
```

```python
class DiscoveryEnvironment:
    nodes: Dict[str, DiscoveryNode]

    def __init__(self, nodes: Dict[str, DiscoveryNode]):
        """Validates every notifies target is a real id in nodes - the
        only structural check this environment does. No cycle-detection
        requirement the way a requires-graph needs one to have a valid
        topological order: a notifies graph can have cycles (A notifies
        B notifies A) without breaking anything, since an agent that's
        already visited a node just doesn't need to revisit it."""

    def sense_edges(self, node_id: str) -> Tuple[str, ...]:
        """Returns nodes[node_id].notifies. Raises ValueError only if
        node_id isn't a real node anywhere in the graph. No arrival
        check - see "Resolved" above."""

    def get_move_cost(self, from_id: str, to_id: str) -> int:
        """Always 1. Same flat-for-now, concept-for-later precedent as
        MazeEnvironment.get_step_cost()."""
```

```python
class DiscoveryAgent:
    def __init__(self, environment: DiscoveryEnvironment, start_id: str):
        """start_id is the agent's own starting position - the
        environment has no concept of a start node, it only ever answers
        sense_edges(node_id) for whatever id it's given."""

    def walk(self) -> DiscoveryWalkResult:
        """Senses outward from start_id, tracking its own current
        position and the set of ids it knows about vs. has visited.
        Moves only to an id present in the current node's already-sensed
        notifies. Stops on reaching a node with no notifies (the goal),
        or once nothing known-but-unvisited remains reachable. Which
        known-but-unvisited id to move to when there's more than one is a
        traversal strategy question, deliberately not fixed by this
        document - see algorithm_fit.md."""
```

```python
@dataclass(frozen=True)
class DiscoveryWalkResult:
    path: List[str]        # nodes visited, in order
    nodes_sensed: int       # how many sense_edges() calls it took
    goal_reached: bool
```

## Where this lives

A new top-level package, `discovery/`, sibling to `maze_solver/`, `task_graph_solver/`, and `path_maintenance/` — not nested inside `path_maintenance/`, since it shares no code with it (see "The edge points the other way" above).

## Not decided

- **Traversal strategy** — DFS-shaped (go deep, backtrack when a node has no unvisited notifies), BFS-shaped, or something else. This document only fixes what the environment allows; `algorithm_fit.md` decides how `DiscoveryAgent` chooses among multiple known-but-unvisited ids.
- **Exact scenario topology** — left to `scenario.md`. Needs exactly one reachable no-`notifies` terminal (see "Resolved: goal" above), and enough branching that traversal strategy actually matters — a linear chain wouldn't exercise the "more than one known-but-unvisited id" case at all.
- **`sense_edges` naming for what it returns** — confirmed as the method name; whether `DiscoveryNode`/`DiscoveryEnvironment`/`DiscoveryAgent` are the right class names, versus something closer to the CI-pipeline framing, is worth a second look once a scenario exists to write tests against (the same "revisit once tests exist" note `graph-topology/environment_design.md` left for its own naming).
