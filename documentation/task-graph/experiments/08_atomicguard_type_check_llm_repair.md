# Experiment 8: `atomicguard`-Backed Repair — an LLM-Based Fix, Wired but Not Yet Run Live

**Run this yourself:** `real_task_graph_solver/atomicguard_backed/tests/test_type_check_repair.py` reproduces every run in this experiment - all eleven tests pass without network access. Animation: [`atomicguard_type_check_clean_free_check.gif`](../../../task_graph_solver/animations/atomicguard_type_check_clean_free_check.gif).

## What this experiment demonstrates, and what it honestly doesn't

Experiment 7 proved `GuardFirstExecutor`'s free-check-then-real-repair pattern against two deterministic repairs (`ruff --fix`, a `sed` edit). This experiment extends the same node shape to a repair that genuinely needs judgement a fixed edit can't provide: `typing_broken`'s wrong return annotation, fixable only by an LLM reading `mypy`'s real error and correcting it. The check half is demonstrated completely, for real, exactly like Experiments 6 and 7. **The repair half is built and dry-run to the actual network boundary, but has never actually succeeded**: this environment's own network policy blocks `openrouter.ai` and `api.openai.com` outright (`curl` against either returns `CONNECT tunnel failed, response 403` - confirmed multiple times, unchanged), so no live call to the LLM could complete, even though one was genuinely attempted. This document says so plainly rather than presenting a repair GIF that would imply otherwise. See [`documentation/task-graph/atomicguard-variant/`](../atomicguard-variant/) for the full design and the reasoning behind every choice below.

## The graph

```mermaid
graph LR
    tc((type-check))
```

One node, same reasoning as Experiments 6 and 7: the point is the repair mechanism, not a new topology.

## Part 1: the free check, for real - `mypy`, no LLM involved at all

On `clean`, `type-check`'s `check_action_pair` (`mypy src/`) passes on the first try - a real, free sensor call, exactly like `lint`/`build-check`.

```mermaid
sequenceDiagram
    participant Agent as GuardFirstExecutor
    participant Env as AtomicGuardCheckEnvironment

    Agent->>Env: check_invariant(type-check) → real `mypy src/` → passed
    Note over Agent: satisfied via a free check - repair_action_pair never runs
```

`result.success is True`; `result.satisfied == {"type-check"}`; `result.free_checks == {"type-check"}`; `env.retries_spent("type-check") == 0`.

### What to watch for in the GIF

One frame beyond the initial white state: `type-check` turns cyan, captioned `check_invariant(type-check) → true`. Nothing else ever runs - the same shape as `lint`/`build-check`'s clean-state GIFs.

## Part 2: the free check genuinely fails, with real `mypy` feedback

`typing_broken` is `clean/` with one line changed: `domain.py`'s `order_total` is annotated to return `str` but actually returns a `float`. `check_action_pair` genuinely fails - real `mypy` output, not a simulated rejection:

```
src/example_pkg/domain.py:16: error: Incompatible return value type (got "float", expected "str")  [return-value]
Found 1 error in 1 file (checked 3 source files)
```

Confirmed directly against the shared DAG's own stored artifact (`env._dag.get_all_for_action_pair("type-check", ...)`), not just the boolean `check_invariant()` returns - the same real-provenance standard Experiment 7's DAG-persistence tests hold everything else in this environment to.

## Part 3: a dry run, a real bug it caught, and where it stopped

`env.attempt("type-check")` was actually run against `typing_broken`, deliberately with a dummy `OR_KEY` - not to fake a repair, but to exercise every real step short of a genuine LLM response. It caught a real bug on the very first call, before the network was ever reached: `PromptTemplate.render()` raises `ValueError: feedback_wrapper must be defined when feedback_history is present` unless `feedback_wrapper` is set, and since `check_action_pair`/`repair_action_pair` share one `action_pair_id`, `feedback_history` is non-empty on the repair's *first* call, always - the check's real rejection is already sitting in the shared DAG. `_REPAIR_PROMPT` had been built without `feedback_wrapper` (following `lint`/`build-check`'s empty-prompt pattern, whose `ExitCodeGuard`-based nodes never call `render()` at all - a gap that only an LLM-shaped generator would expose). Fixed with `feedback_wrapper="mypy reported this error:\n{feedback}"`; `test_repair_prompt_template_renders_with_feedback_history_present` proves it directly, without network, by rendering the real prompt template against a `Context` carrying real feedback.

Re-running the dry run afterward reached the actual OpenRouter connection attempt cleanly and failed only there - `pydantic_ai.exceptions.ModelAPIError: Connection error`, caught internally by `LLMContainerFixGenerator`'s own exception handling, surfacing as a genuine `RmaxExhausted` and `AttemptOutcome.FATAL`. `env.time_spent("type-check")` measured ~17-22s of real, exhausted retry attempts - the actual cost of `DualStateAgent`'s `repair_rmax` retries each hitting a blocked connection. Confirmed for both candidate models.

Two real gaps remain, recorded rather than hidden:

- **Neither model slug is confirmed against OpenRouter's live catalog.** `google/gemini-2.5-flash-lite` is a reasonable guess; `deepseek/deepseek-v4-flash` is genuinely uncertain (DeepSeek's known naming runs v3/v3.1/v3.2/R1, not v4 - this could be a newer release, or could simply be wrong). A network-layer connection error, which is all either candidate has produced so far, can't distinguish "blocked" from "wrong model ID" - a real live attempt, once network access exists, might still fail with a 400 rather than succeed.
- **No successful repair has happened yet.** This experiment can now say the pipeline is correctly wired end to end up to the network boundary - not that `LLMContainerFixGenerator`'s feedback-driven fix actually produces a correct annotation.

### What to watch for - or rather, what isn't here yet

No repair GIF exists for this node, deliberately. Generating one would require an actual successful LLM call this document just explained hasn't happened - doing so anyway (e.g. by faking the generator's output) would be exactly the kind of declared-not-demonstrated pass this whole project's testing discipline exists to avoid.

## What this experiment validates that a repair GIF alone could not have

Everything up to and including the network boundary is real: real `mypy`, a real fixture, real feedback captured in a real, persistent, on-disk DAG, a repair Action Pair whose every configuration detail is correct and tested, and a dry run that found and fixed a genuine bug (`feedback_wrapper`) no wiring test alone would have caught. The honest gap - no *successful* live LLM call, two unverified model slugs - is exactly the kind of limitation this project's discipline asks to be recorded plainly rather than smoothed into an implied success. A follow-up experiment, once network access exists, is a single real command away: the same `env.reset_to_state("typing_broken")` / `env.attempt("type-check")` pair already exercised here, checking that `order_total`'s return annotation actually changed to `-> float` and that `mypy` now genuinely passes.

## Related experiments

- [Experiment 7: `atomicguard`-backed deterministic repair](07_atomicguard_lint_repair.md) - the two repairs demonstrated completely, end to end, that this experiment's LLM-based repair is built on the same pattern of but cannot yet complete the same way.
- [Experiment 6: Real Guards](06_real_guards_release_pipeline.md) - `typing_broken`'s fixture state and `mypy` check were both established there, reused unmodified here.
