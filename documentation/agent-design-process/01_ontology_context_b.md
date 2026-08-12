## PEAS for the minimal LLM loop

| Element | This agent |
|---|---|
| **Performance** | Produce a final answer to the prompt — success is signaled by the model itself (`stop-check` = the `"FINAL:"` prefix). No accuracy check against ground truth, and no cost/turn budget — it just trusts the signal and stops. |
| **Environment** | The LLM service (`llm-query`'s target) + the user (supplies the initial prompt, then nothing further — no follow-ups, no permission answers). |
| **Actuators** | `LLM.QUERY(context)`, `REPORT(response)`. That's the entire action vocabulary — nothing else is emitted. |
| **Sensors** | The prompt (from the user), the model response (from `LLM.QUERY`). Nothing else arrives as a percept. |

## Environment analysis — and what stripping tools/DSA actually cost you

Worth doing this side-by-side with the fuller `ag-agent` from the `dev` repo, because several properties that looked substantive there get thin or flip here — not because the framework is wrong, but because you removed the thing that gave them content:

| Property | This toy | Full `ag-agent` | Why the gap |
|---|---|---|---|
| **Structurally known / observationally unknown** | Thin — only the *percept/action vocabulary* is fixed in advance (prompt/response, `LLM.QUERY`/`REPORT`); there's no loaded ontology | Rich — a loaded ontology: types, D3-kinded predicates, `:derived` rules known before any sensing | You stripped `belief` and the domain model entirely — there's nothing to sense *about*, so the environment's headline property loses its substance |
| **Partially observable** | Yes, but trivially — the agent cannot verify its own answer is correct; it just trusts the LLM's self-declared `"FINAL:"` | Yes, richly — tool-mediated, result-lossy, result-attributed across many sources | Same property, much shallower cause — one unverifiable signal instead of many fallible tool results |
| **Stochastic** | Yes in principle (the real client would be); this toy's stub is deterministic | Yes | unchanged in kind |
| **Sequential** | Sequential in structure (context accumulates turn to turn) — but `stop-check` here only looks at the turn counter, not accumulated content, so the design isn't actually exercised | Sequential, and exercised (belief/declared state genuinely carry across turns) | The wiring is there; nothing uses it yet |
| **Dynamic vs static** | **Static** — nothing outside the LLM and the user can change between turns, because there's no external world being sensed (no files, no CI, no tools) | Dynamic — files/services change between reads, results are timestamped | A direct, honest consequence of removing tools — dynamism was never a property of the loop itself, it came from the *world the tools touched* |
| **Single/multi-agent** | Single-agent — the LLM is a stochastic service/oracle, not a strategic participant; no subagents, no permission asks, no notify/escalate | Multi — subagents, the human as a real participant, plus the agent's own Layer-2 self-observation | Removing delegation and control-transfer removes everything that made it "multi" |
| **Known** | Known — `llm-query`/`stop-check`'s "physics" are fully hardcoded | Known (structurally) | unchanged |
| **Discrete** | Yes — 2 actuators, 2 percept kinds | Discrete but much larger vocabulary | unchanged in kind, smaller in degree |

Two things worth naming directly rather than papering over:

1. **The two-layer environment from `environment-analysis.md` mostly collapses here.** That doc's whole point was that the agent produces *and* consumes its own Layer 2 (declared state, belief, obligations) — but this toy has no `Intent`, no `Todo`, no derived-obligation closure, nothing to `NOTIFY`/`ESCALATE`. `context` is the only state, and it's pure Layer-1 conversation history, not a self-model. So there isn't really a second layer yet — it shows up the moment you add tools (an outcome to merge into belief) or declared state (a todo to update), not before.

2. **The Performance Measure is the weakest row, on purpose — and it's the same critique your own IA10 post made about Claude Code.** `stop-check` trusts the model's self-reported `"FINAL:"` with zero external check. That's not a bug in the toy, it's an accurate PEAS finding: as written, this agent's performance measure is entirely self-attested by the same stochastic process being measured — which is close to the "irrational performance measure" problem you flagged in December (you can't debug what you can't independently verify). The natural next fix isn't more Hy — it's a `REPORT` that carries evidence, which is exactly what `agent-function.md`'s `REPORT(Ψ, belief, evidence)` adds once there's a `belief` to cite.
