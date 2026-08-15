# A Kind for stochastic reasoning — reserved

*Draft. Not part of the series. Created while writing IA 14, when the reported channel was removed from the post.*

## The observation

IA 14 originally framed belief acquisition as two channels: **sensed** (the world — a node's `notifies`, `requires`) and **reported** (the model's reasoning — `"FINAL:"`). The reported channel was dropped from the post because it maps to **no existing Kind**:

| Kind | Who determines truth | Reported fit? |
|---|---|---|
| exogenous | the world | no — a model conclusion isn't world-determined |
| controllable | the agent | no — it's not the agent's own declared assertion |
| derived | its base atoms (symbolic entailment) | no — the model reasons stochastically, not by entailment |
| static | fixed | no |

The model's `"FINAL:"` is a **self-attested stochastic judgement** — a fifth category sitting outside the Kind taxonomy.

## The distinction this surfaced

Kind and channel are different axes:

- **Kind** = *who determines the atom's truth* (justification structure)
- **Channel** = *how a belief arrives* (transport)

The two-channel framing smuggled in a transport axis the Kind-based ontology has no slot for. Keeping the post's belief state strictly world-ontology — sensed and derived facts only — keeps it consistent with Kind.

## Why it was removed

No current work links stochastic reasoning into the ontologies. The model's `"FINAL:"` belongs to the LLM-agent work (self-consistency, confidence), not to the belief-state/ontology thread. There was nothing to anchor a fifth Kind to, so it was cut rather than forced in.

## How a future Kind would fit

When there is work that links stochastic reasoning into the ontologies, introduce a Kind such as **attested** (or `self-attested`):

- **Justification:** the model's stochastic reasoning determines truth — self-attested, no world grounding to re-sense against.
- **Management:** confidence, not re-sensing. A self-attested belief cannot be checked against the world; it is judged.
- **Boundary:** it would mark where the freshness axis stops — `:fresh-for`/`:stale-on` do not apply to a judgement that cannot be re-sensed.
- **Agent type:** the reasoning channel is stochastic (IA 12), distinct from the symbolic reasoning the belief state does (IA 11).

## Status

Reserved, not open. Revisit when there is real work connecting model reasoning to the ontology thread.
