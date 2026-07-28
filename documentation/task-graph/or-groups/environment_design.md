# OR-Groups and an Explicit Goal: Environment Design

## Purpose

Every scenario built so far (`disk_check_lite`, `repair_packages_lite`, `pr_merge_lite`) uses `requires` as pure AND-composition, and `ExecutionResult.success` means "every declared node ended up satisfied." Combined, these two choices make a structural guarantee that's been true of every experiment in this repo until now: **every node `ready_nodes()` ever returns is, by construction, necessary and correctly sequenced.** There is no way for an agent to make a wrong-but-legal choice, because there are no alternatives to choose between and nothing in the graph is optional.

`atomicguard`'s own archived design notes (`docs/archive/notes/2026-02-25T18-multi-path-rl-design.md`) hit this exact wall in the real system: an 18-AP Django workflow was "effectively a corridor with one exit," and the RL agent "had almost no decision surface... learning 'execute in dependency order and hope gen_patch works,' not a real strategy." Their proposed fix — **variant APs sharing a slot, where satisfying any one unblocks downstream** — is the real-world origin of what this document designs for the toy environment: OR-groups, plus a goal distinct from "everything satisfied," so that a node can exist, pass its own guard, and still not matter.

This document specifies the environment changes only. [`scenario.md`](scenario.md) specifies the concrete toy graph. [`algorithm_fit.md`](algorithm_fit.md) walks through how each of the four existing algorithms behaves differently once these exist.

## The problem, precisely

`environment_design.md` (the original) already gives `requires` a first-class AND-composition role. What's missing is any way to express "any one of these" — and without that, "waste" (attempting something that turns out not to be needed) can never happen, because nothing is ever *not* needed.

## Two new concepts

### 1. `GroupNode` — an OR-composition over existing nodes

An OR-group is **not** a `TaskNode`. It has no Guard, no `pass_probability`, no `rmax` — nothing is *attempted* to satisfy it. It's a derived, logical construct:

```python
@dataclass
class GroupNode:
    """An OR-composition: satisfied the instant any one of `members` is
    satisfied. Not attempted directly - there is no Guard to run, no
    retry budget to exhaust. Downstream nodes list the group's id in
    their own `requires` tuple exactly as they would a normal node id;
    the AND-gating check treats a group id and a plain node id
    identically from the outside.

    Mirrors the real, still-unresolved design question in atomicguard's
    own archive: "either a group field on APs, or downstream requires
    referencing a group name rather than a specific AP." This design
    picks the second option - members stay ordinary TaskNodes, nothing
    about TaskNode itself changes, and the group is purely an
    aggregation referenced by id from the requires side.
    """
    id: str
    members: Tuple[str, ...]  # ids of TaskNodes, all with the same requires
```

Satisfaction check (conceptually — see `algorithm_fit.md` for exactly where this plugs into `ready_nodes()`):

```
is_satisfied(id, satisfied):
    if id is a GroupNode id:
        return any(member in satisfied for member in group.members)
    else:
        return id in satisfied  # unchanged, plain node check
```

Because `ready_nodes()`'s AND-gating (`all(dep in satisfied for dep in node.requires)`) only ever needs to ask "is this dependency satisfied," swapping the plain membership check for `is_satisfied()` handles *both* AND and OR dependencies through the same code path. **No executor needs to change to get basic gating right** — `TopologicalExecutor`, `AOStarExecutor`, and `DStarLiteExecutor` all correctly unblock a downstream node the instant any one group member passes, with zero changes to their `step()`/`run()` logic. What *does* differ between them is covered in `algorithm_fit.md`: none of them currently know to **stop attempting a group's other members once the group is already satisfied** — that's a real, new, algorithm-specific capability, not something the environment can give away for free.

An OR-group is unsolvable only once **every** member is fatal or transitively unreachable — the inverse of an AND-node, which is unsolvable if **any** required child is.

### 2. An explicit goal, distinct from "all nodes satisfied"

```python
class TaskGraphEnvironment:
    def __init__(self, nodes, config, groups=(), goal=None):
        ...
```

```python
@dataclass
class ExecutionResult:
    # existing fields unchanged: satisfied, fatal, unreachable, trace
    goal_reached: bool  # NEW - True iff `goal` is in `satisfied`
    # `success` becomes an alias/property for goal_reached, not
    # `satisfied == all_nodes` - a scenario can finish with pending or
    # never-attempted nodes and still be a full success.
```

Without this, nothing can be a genuine dead end — every declared node is implicitly load-bearing, because the run only counts as a success once all of them pass. With an explicit `goal`, a node can exist, be perfectly attemptable, pass its own guard cleanly, and still be irrelevant to whether the run succeeded.

## Two kinds of "doesn't help the goal" — worth keeping distinct

These are not the same failure mode, and conflating them would blur exactly the thing this extension exists to demonstrate:

| | Losing OR-sibling | True orphan |
|---|---|---|
| Is it part of the graph structure feeding the goal? | Yes — a member of a group that *does* unblock the goal | No — nothing downstream of it requires it, directly or transitively |
| Why attempting it is wasteful | Only if a *different* sibling already satisfied the group, or will — attempting this one too spends budget the group didn't need | Always — there was never a scenario where attempting it helps reach the goal |
| Which algorithm capability addresses it | AO*'s early-stop-on-satisfied-group (new, see `algorithm_fit.md`) | Nothing addresses it — it's meant to just sit there; a good agent might simply never attempt it if it never becomes relevant to the goal's dependency chain |
| Real-world analogue | `gen_patch_comprehensive` succeeding after `gen_patch_minimal` already passed | An unrelated lint check nobody's release gate depends on |

## Not decided

- **Cost composition through a group for AO*.** `h(AND-node)` uses `max` over required children (`documentation/task-graph/algorithm_fit.md`'s existing rule). What should `h(group)` be once satisfied — the cost of whichever member actually passed (the honest answer, since that's the only one truly known), or `min` over all members' costs if more than one happened to be attempted before the group was recognized as satisfied? Needs settling before `AOStarExecutor` is extended, not before this design doc.
- **Whether `GroupNode` needs its own retry-adjacent concept.** A plain `TaskNode` has `rmax`/`r_patience`; a group has neither, by design — but is there a scenario where "give up on this slot after N total attempts across all members" matters? Left open; the toy scenario in `scenario.md` doesn't need it.
- **Whether non-goal nodes left pending at the end should be reported distinctly from `unreachable`.** Right now a losing OR-sibling that was never attempted (because a faster sibling already satisfied the group) would fall into neither `satisfied`, `fatal`, nor a genuinely-blocked `unreachable` — it's just never attempted, which existing `ExecutionResult` fields don't have a clean label for. Worth a field like `never_needed` once this is implemented, not decided here.
