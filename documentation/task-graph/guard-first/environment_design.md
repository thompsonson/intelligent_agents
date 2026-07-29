# Guard-First States: Environment Design

## Purpose

Every executor built so far (`TopologicalExecutor`, `AOStarExecutor`, `DStarLiteExecutor`) treats "attempt a node" as one atomic, budget-consuming operation: `env.attempt(node_id)` always runs the full simulated generate-and-repair cycle, whatever the node's actual state already is. There's no way, today, for a node to say "check first — I might already be true, for free, before you pay for a repair."

That's not a hypothetical gap. It's the exact shape of a real, checkable gap in `atomicguard`'s own `ActionPair.execute()` (`atomicguard/src/atomicguard/application/action_pair.py`):

```
Phase 1: a_gen = generator.generate(context)        # ALWAYS runs, unconditionally
Phase 2: G_pre(a_gen) → if fail, return (no side effects yet)
Phase 3: a_exec = E.execute(a_gen)                  # world state mutated
Phase 4: G_post(a_exec) → final verdict
```

`G_pre` validates `a_gen` — the artifact the generator just produced — not the live world. There is no phase that asks "does the invariant this Action Pair exists to establish already hold, before we generate anything at all?" Every single visit to an Action Pair pays for a full generator call (an LLM invocation) even when the underlying condition is already satisfied — e.g. a PR that's already merged, a package that's already installed, a disk that already has space. The closest thing that exists is `WorkflowOrchestrator.resume_from()` (`application/workflow.py`), which skips already-satisfied steps — but only by replaying a *persisted* DAG of prior accepted artifacts, not by live-sensing the current world state.

The theoretical grounding for why this gap is worth closing is already sitting in `atomicguard/docs/design/notes/mark_burgess_correspondence.md`: Mark Burgess's own read of the paper is that Guard Functions are "essentially a rewriting... of CFEngine" — a desired-state convergence system where you *check* whether a promise already holds before you *do* anything to establish it. That's precisely the "check-first" pattern this document designs a toy version of. It's also already half-true in the code: `ContainerSubprocessGuard.validate(artifact, **dependencies)` (`infrastructure/guards/container_subprocess_guard.py`) doesn't even read its `artifact` argument (`# noqa: ARG002`) — it runs a fresh subprocess and senses the container's actual state every time. Guards like this are *already* artifact-independent sensors; they're just never invoked before generation today.

`scenario.md` (not yet written) will specify a concrete toy graph. `algorithm_fit.md` (not yet written) will contrast the new executor against `TopologicalExecutor` on that scenario, mirroring the OR-groups build order.

## The core idea

Every node in this environment already models a DS-PDDL Action Pair. What's missing is the ability for a node to expose a *cheap, non-consuming* check of whether it's already satisfied, separate from the *costly, budget-consuming* repair. Concretely:

```python
@dataclass
class TaskNode:
    ...
    invariant_pass_probability: float = 0.0
```

- **Default `0.0`** — every existing scenario (`disk_check_lite`, `repair_packages_lite`, `pr_merge_lite`, `pr_merge_with_variants`) needs zero changes; a node that never opts in behaves exactly as it does today, since a 0.0 chance of already being satisfied always falls through to the existing repair path.
- **A scenario that opts in** sets this above 0.0 for nodes whose real-world counterpart could plausibly already hold — the toy equivalent of "this package might already be installed from a previous, interrupted run," which is a story `repair_packages_lite` can tell honestly without inventing a new domain.

New environment method, alongside `attempt()`:

```python
def check_invariant(self, node_id: str) -> bool:
    """A free sensor: draws from `invariant_pass_probability`, consumes no
    retry budget, callable repeatedly, mirrors a live-sensing Guard called
    before any generation happens. Does not mutate `_attempts_made` or
    `_consecutive_failures` - this is the toy-environment equivalent of
    ContainerSubprocessGuard's "runs the command itself on every call,
    providing fresh sensing" (found reading the real Guard, not invented
    for this design). Independent of `pass_probability` - a node's
    already-satisfied chance and its post-repair pass chance are not
    required to be related."""
```

This needs its own RNG draw (same `self._rng`, same seeded-determinism property every other `TaskGraphEnvironment` method already has), and — like `attempt()` — should be blocked by `break_task`: a node the Driver has forced broken must never report itself as already-satisfied, or D* Lite-style scenarios built on top of this would have a hole in them.

## The new executor: `GuardFirstExecutor`

Modeled directly on `TopologicalExecutor` — same sorted-by-id frontier selection, same "drive to a terminal outcome" loop — with one addition inserted before the existing repair loop:

```python
def step(self) -> bool:
    ready = sorted(...)  # unchanged from TopologicalExecutor
    if not ready:
        return False

    node_id = ready[0]

    if self.env.check_invariant(node_id):
        self.satisfied.add(node_id)
        self.free_checks.add(node_id)   # NEW - see below
        return True

    # Guard didn't already hold - fall through to the existing repair loop,
    # unchanged from TopologicalExecutor.
    outcome = AttemptOutcome.RETRY
    while outcome == AttemptOutcome.RETRY:
        outcome = self.env.attempt(node_id)
        self.trace.append((node_id, outcome))
    ...
```

`self.free_checks: Set[str]` is new and deliberately not folded into `trace` (which only ever records paid `attempt()` outcomes) or into `ExecutionResult.satisfied` and `not_needed` — it needs its own name because it's neither. It isn't `not_needed` (that field means "a losing OR-sibling nobody had to attempt because a group was already satisfied by something else" — a *different* node did the work). Here, the *same* node's own invariant simply already held. Worth a field on `ExecutionResult` — `free_checks: Set[str] = field(default_factory=set)` — so a test can assert the measurable, demonstrable thing this design exists to show: **zero repair attempts spent on nodes whose invariant already held**, the same "measurable quantity" framing the OR-groups `not_needed` field established.

### Why `TopologicalExecutor` stays exactly as it is

Same reasoning as the OR-groups baseline: `TopologicalExecutor` never calls `check_invariant()` at all, so on an identical scenario it always pays full repair cost for every node — including ones whose invariant was already free to check. That's not a bug to fix in `TopologicalExecutor`; it's the same "no heuristic, no learning, no repair" baseline role it's always played, and the waste is now a measurable, contrastable quantity, the same way OR-group waste became one.

### Why this isn't AO* or D* Lite

Neither existing algorithm is the right place for this. AO*'s new capability (pruning a satisfied OR-group's losing siblings) is about *not exploring alternatives once one is known to work* — a different question from *"is this specific node already true without exploring anything."* D* Lite's capability is about *sensing exogenous change to nodes already given up on* — again a different axis (recovery after failure, not avoidance of unnecessary work up front). `GuardFirstExecutor` is its own, narrower thing: a baseline-shaped executor that adds exactly one capability, check-before-repair, the same way `AOStarExecutor` added exactly one capability (AND-composition) on top of the topological baseline.

## What this would take in the real `atomicguard` system (not building yet)

Flagging concretely, grounded in the exact code read for this document, not a vague "could extend this later":

- **`GuardInterface` needs no interface change.** `ContainerSubprocessGuard` and similar sensing guards already ignore their `artifact` parameter — they're already capable of being called before any generation happens. The gap is entirely in when `ActionPair.execute()` chooses to call the guard, not in what guards are capable of.
- **`ActionPair.execute()` would need a genuine Phase 0**, before Phase 1: if a "state guard" is configured (could reuse `self._guard`, the same instance used for `G_post`, since a sensing guard's validate() behaves identically regardless of when it's called) and it already passes against the live world, return an `ActionPairResult` immediately, skipping generation and the effector entirely.
- **`FailurePhase` (`domain/interfaces.py`) would need a new value** — something like `ALREADY_SATISFIED` — distinct from `PASSED`, exactly for the reason `not_needed` needed to be distinct from `satisfied` in the OR-groups work: "we generated and repaired and it passed" and "it was already true, we touched nothing" are different facts a caller (telemetry, a learning agent, a human reading a trace) would want to tell apart.
- **`Idempotency` (`EffectorInterface`) is related but must not be conflated.** `Idempotency.IDEMPOTENT`/`NON_IDEMPOTENT` answers "is it safe to re-run the effector if we're unsure it already ran" — a retry-safety question. What Phase 0 needs is a different question: "is it safe/cheap to check the guard *before ever running the effector at all*." An idempotent effector doesn't imply a pre-checkable guard, and a pre-checkable guard doesn't imply the effector is idempotent — worth a separate flag (maybe on the Action Pair itself, e.g. `pre_checkable: bool`), not a reuse of `Idempotency`.
- **This is a genuine cost-saving feature for the real system**, not just a toy exercise: every Action Pair visit that could have been a free check instead pays for a full LLM generation call today. The toy environment's `invariant_pass_probability` is a simplified stand-in for "how often is this condition already true when we get here" — a real, measurable quantity a production system could actually estimate from history.

## Not decided

- **Exact `invariant_pass_probability` values for the first scenario** — left to `scenario.md`.
- **Whether `check_invariant()` should count toward `retries_spent()` at all**, even as a zero-cost entry. Leaning toward "no" — it's not a retry, it's a sensor — but worth confirming once a scenario exists to test against.
- **Whether a node can have `invariant_pass_probability > 0` and `retry_flavor="repair"` simultaneously** without contradiction. Current answer: yes, no contradiction — the two describe different phases (is it already true vs. what kind of retry a repair represents if it isn't), but this hasn't been exercised by a real scenario yet.
