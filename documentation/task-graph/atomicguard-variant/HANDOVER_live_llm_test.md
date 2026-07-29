# Handover: run `type-check`'s LLM repair live against OpenRouter

**Why this exists:** the session that built `type-check`'s LLM-based repair (`real_task_graph_solver/atomicguard_backed/scenarios/type_check_repair.py`) runs in a sandbox whose network policy blocks `openrouter.ai` and `api.openai.com` outright (`curl` returns `CONNECT tunnel failed, response 403` - confirmed repeatedly, unchanged). Everything is built, wired, and tested up to that boundary - a dry run with a dummy key even caught and fixed a real bug (a missing `feedback_wrapper`) before ever reaching the network. What's missing is the one thing that session cannot do: an actual network round-trip to a real LLM. If you're reading this, you're in a session that *can* reach OpenRouter - this document is everything you need to finish the job without any other context from that session.

**Starting point:** branch `claude/d-star-toy-example-b7knlm`, commit `2de5d6c` or later. `git pull` first to make sure you have this file and everything it references.

## What's already true, don't re-derive it

- `real_task_graph_solver/atomicguard_backed/` has three repair nodes: `lint`, `build-check` (both deterministic, fully proven, not your concern), and `type-check` (LLM-based, the subject of this handover).
- `type-check`'s `check_action_pair` is a free, real `mypy src/` check. Its `repair_action_pair` uses atomicguard's real `LLMContainerFixGenerator` (host mode) against OpenRouter, guarded by `ContainerSubprocessGuard` re-running `mypy`.
- The API key is read from the `OR_KEY` environment variable (`core/llm_config.py`'s `openrouter_api_key()`). Model defaults to `google/gemini-2.5-flash-lite` (`DEFAULT_MODEL` in that same file); `deepseek/deepseek-v4-flash` is the other candidate named, equally unverified.
- **Neither model slug has been confirmed against OpenRouter's real catalog.** This is the single most likely source of a first-run failure that has nothing to do with the LLM's actual capability.
- The fixture being repaired: `real_task_graph_solver/fixtures/example_pkg/typing_broken/src/example_pkg/domain.py` - `order_total`'s return annotation says `str`, the function actually returns `float`. A correct fix changes the annotation (most naturally to `-> float`), not the function body.
- 213 tests currently pass without network (`uv run pytest task_graph_solver/ real_task_graph_solver/tests/ real_task_graph_solver/atomicguard_backed/ -q`). None of them call a real LLM. Keep them passing - don't touch this suite except to add to it.

## Step 1: confirm the model slugs

Check `https://openrouter.ai/models` for the real, current slug of "Gemini 2.5 Flash Lite" and "DeepSeek V4 Flash" (or whatever DeepSeek model is closest to that name today - it may not exist under that exact name; use your judgement and pick the closest real, current model if not). If either differs from what's in `core/llm_config.py`, fix the constants there and update the comment above them (it currently says neither slug could be verified - once you've confirmed one, say so and remove that caveat for the one you confirmed).

## Step 2: run the live validation

Save this script **outside the repo** (matching this project's own convention - GIF-generation and validation scripts are never committed, only their outputs) and run it:

```python
"""Uncommitted validation script - not part of the repo."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/home/user/intelligent_agents")  # adjust to your repo root

from real_task_graph_solver.atomicguard_backed.core.environment import (
    AtomicGuardCheckEnvironment,
)
from real_task_graph_solver.atomicguard_backed.core.llm_config import (
    DEFAULT_MODEL,
    OR_KEY_ENV_VAR,
    openrouter_api_key,
)
from real_task_graph_solver.atomicguard_backed.scenarios.type_check_repair import (
    BROKEN_STATES,
    FIXTURES_DIR,
    build_type_check_repair,
)
from task_graph_solver.core.domain import AttemptOutcome


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL

    try:
        openrouter_api_key()
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}")
        print(f"  export {OR_KEY_ENV_VAR}=<your real OpenRouter key> and retry.")
        return 1

    print(f"Using model: {model}")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp) / "workdir"
        nodes, goal = build_type_check_repair(workdir, model=model)
        env = AtomicGuardCheckEnvironment(
            nodes,
            fixtures_dir=FIXTURES_DIR,
            workdir=workdir,
            goal=goal,
            broken_states=BROKEN_STATES,
        )

        env.reset_to_state("typing_broken")
        domain_py = workdir / "src" / "example_pkg" / "domain.py"
        before = domain_py.read_text()

        print("--- domain.py before ---")
        print(before)

        print("Checking (free, real mypy)...")
        check_passed = env.check_invariant("type-check")
        print(f"  check_invariant() -> {check_passed}")
        if check_passed:
            print("UNEXPECTED: typing_broken already passes mypy - fixture problem?")
            return 1

        print("Attempting real repair (this makes a real network call to OpenRouter)...")
        outcome = env.attempt("type-check")
        after = domain_py.read_text()
        elapsed = env.time_spent("type-check")

        print("--- domain.py after ---")
        print(after)
        print(f"outcome: {outcome}")
        print(f"time_spent: {elapsed:.2f}s")
        print(f"file changed: {before != after}")

        if outcome == AttemptOutcome.PASS:
            print("SUCCESS: real LLM repair resolved the type error.")
            return 0

        print("FAILED: attempt() did not resolve the type error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it with `OR_KEY` set: `uv run python live_type_check_repair_test.py` (or pass a model slug as `argv[1]` to override the default). If it fails with something that looks like a 400 / "model not found" rather than a genuine repair failure, that confirms a bad slug - go back to Step 1.

## Step 3: depending on what happens

### If it succeeds (`AttemptOutcome.PASS`, file genuinely changed, `mypy` now passes)

1. **Generate the real repair GIF.** Reuse the exact pattern already used for `lint`/`build-check` in `task_graph_solver/visualization/graph_view.py`'s `record_events`/`animate_events` - see `real_task_graph_solver/atomicguard_backed/tests/test_lint_repair.py`'s equivalent success case and the (uncommitted) GIF-generation pattern referenced in `documentation/task-graph/experiments/07_atomicguard_lint_repair.md` for the shape. Save it as `task_graph_solver/animations/atomicguard_type_check_broken_real_repair.gif` (matching the naming convention of the other two nodes' repair GIFs) and commit it.
2. **Update three docs**, replacing the "not yet run live" framing with the real result - follow the exact pattern already used for `lint`/`build-check` in each:
   - `documentation/task-graph/atomicguard-variant/algorithm_fit.md` - the `type-check` section currently ends with "What's real here... What's not yet real: an actual successful LLM call." Replace with the real outcome: what the LLM actually changed, confirmed by hand (before/after file content), same as the `lint`/`build-check` sections above it.
   - `documentation/task-graph/experiments/08_atomicguard_type_check_llm_repair.md` - retitle away from "Wired but Not Yet Run Live," add the repair GIF, write it up the same way Experiment 7 documents `lint`/`build-check`'s real repairs (with a "What to watch for in the GIF" subsection).
   - `TASK_GRAPH_SOLVER.md`'s `atomicguard`-backed repair section (search for "No repair GIF exists for this node") - update to describe the real GIF and result, matching the `lint`/`build-check` paragraphs immediately above it.
3. **Add a real integration test** (`test_type_check_repair.py`, following `test_lint_repair.py`'s `test_lint_broken_state_is_genuinely_repaired_not_just_declared_fixed` pattern) - but mark it to skip without `OR_KEY` set (`pytest.mark.skipif`), since this suite must keep passing without network for whoever runs it next without a key.
4. **If you had to correct the model slug**, make sure `DEFAULT_MODEL` in `core/llm_config.py` points at the one that actually worked, and the comment above it reflects reality (confirmed, not guessed).
5. Run the full suite (`ruff check`, `black --check`, then all three test directories) before committing.
6. Commit and push to `claude/d-star-toy-example-b7knlm`, following this repo's existing commit style (see `git log` for tone and the `Co-Authored-By`/session footer convention already in use).
7. **Delete this handover file** (`documentation/task-graph/atomicguard-variant/HANDOVER_live_llm_test.md`) as part of that commit - it's a transient coordination artifact, not part of this project's permanent documentation set once the work it describes is done.

### If it fails for a real reason (not a bad model slug)

Record it exactly like every other finding in this project's history: don't hide it, don't retry silently until it passes. Update the same three docs to say precisely what happened - the exact error, whether it was a network issue, a guard failure, or the LLM producing an incorrect fix - and leave `type-check`'s repair explicitly marked as attempted-but-unresolved rather than either "not yet tried" (no longer true) or "working" (not true either). This project's whole discipline is recording corrections and limitations honestly rather than smoothing them over - that applies here too.

## What not to do

- Don't touch `lint`/`build-check` - they're fully proven, not in scope here.
- Don't fake or hand-write a "repair" GIF from a run that didn't actually happen.
- Don't remove the `OR_KEY`-gating or make network access implicitly required for the existing test suite - it must keep passing for anyone without a key.
- Don't build `architecture-test`'s LLM-based repair as part of this handover - that's the next, separate phase, same pattern, out of scope here.
