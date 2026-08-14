# [IA Series 15/n] Five Layers

*Draft. The layer model the [belief-state post](../14-managing-belief-state/blog.md) sits within — the full frame for an agent working an unknown world.*

## The five layers

An agent working an unknown world operates over five layers, each distinct from the others.

A generalization of the **Dual-State Architecture** in [Managing the Stochastic (Thompson 2025)](https://arxiv.org/abs/2512.20660v1): that paper split the agent's state between deterministic workflow control and the stochastic environment where the LLM lives — the LLM treated as a component of the environment, not the decision-maker. These five layers keep that boundary — NL reasoning is the environment's stochastic generation, Declared the deterministic workflow control — and add the world, the belief state, and the repository the dual-state framing left implicit.

| Layer | What it holds | Source | Reasoning |
|---|---|---|---|
| **World** (ontic) | the actual infra estate | mutable; observed via sensing — copies only | — (it *is*; not reasoned) |
| **Belief** (epistemic) | held copies of world facts — a projection of the repository | append-only; the agent's model | symbolic — atoms, predicates, the derived closure (the grammar of logic, IA 11) |
| **NL reasoning** | the LLM's reasoning context — where the model thinks | the generator; self-attested | stochastic — the model's generation, a component of the environment (IA 12) |
| **Repository** | generator artifacts + effector output + guard verdicts + sensed facts — the append-only artifact DAG | the single evidentiary store | — (an evidentiary store, not a reasoner) |
| **Declared** | the agent's own commitments and workflow state | the agent's intent | symbolic — the agent's stated commitments |

## The relationships that matter

- The belief state **reads from the repository** — it is a projection of it, not a parallel store. The repository holds the evidentiary record; the belief state is the view the agent reasons over. The repository is the artifact DAG; the belief state is its projection — it holds graph-shaped facts (edges, requirements) but is not itself a DAG.
- **Belief and Declared are two projections of the same repository**: the belief state is the repository projected onto the world model; the declared is the same repository projected onto the workflow's requirements — plus the agent's own commitments.
- The NL reasoning is self-attested and ephemeral; the repository is durable and verified.

One ontic world behind them all. The belief state is the projection the agent reasons over; the NL reasoning is where the model thinks; the repository is the single store everything reads from; the declared is the agent's own commitments.

## The ontologies

[IA 13 drew the split](../13-ontologies/blog.md) between the world ontology and the agent ontology. Across the five layers the divide runs cleanly: what the agent **discovers** — the world's facts, and the declared freshness bounds — is **world ontology**; the **belief-state lifecycle** and the management actions are **agent ontology**, the agent's own machinery. The belief state is where the two meet: it holds world-ontology facts, managed by the agent-ontology lifecycle.

## The belief state

The belief state is the subject of [IA 14](../14-managing-belief-state/blog.md) — its drift from the ontic world, the two channels it arrives through, and the freshness axis that keeps it in sync. These five layers are the frame it sits within.
