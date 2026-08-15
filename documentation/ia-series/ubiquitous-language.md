# Ubiquitous Language

*Living document. The shared naming and vocabulary for the series' [domains](domains.md), agreed so every design document means the same thing by the same word. Two artefacts fail differently: the domains decide **where a term belongs**; this document fixes **what each term means**.*

*Source of truth: the posts remain authoritative for the terms they establish. This document is the living extract — when a post changes a term, update it here so the two don't drift apart silently.*

## The grammars (substrate — referenced, not absorbed)

The domains are written in two languages, each given its own term sheet:

- [The Grammar of Logic](../11-grammar-of-logic/blog.md) — how an agent reasons. Terms carried into the ontology: **predicate**, **atom**, **sentence**, **entailment (⊨)**, **derivation (⊢)**, **knowledge base (KB)**, **model**, **determination** (truth is attributed by a human-chosen model, not discovered).
- [The Grammar of Natural Language](../12-grammar-of-natural-language/blog.md) — how an agent communicates. Terms carried in where meaning meets the world: **sense**, **reference**, **compositionality**, **distributional semantics** (meaning determined by the corpus, not attributed), **truth conditions**, **speech acts**.

These are not domains; they are the languages the domains are expressed in.

## Domain: World ontology

The environment the agent navigates and acts in.

**Entities:**

| Term | Agreed meaning |
|---|---|
| `Node` | a stage in the estate — `commit`, `lint`, `unit-tests`, `merge-gate`, `deploy` |
| `Edge` | a connection between nodes, in one of two directions |
| `Domain` | the system a topology lives in |
| `Status` | a node's condition from the agent's point of view — known, visited, cleared, blocked |

**Predicates:**

| Term | Kind | Agreed meaning |
|---|---|---|
| `node(id)` | exogenous | sensed — the node exists in the estate |
| `notifies(id, target)` | exogenous | sensed per node — the push edge, who this node tells when it finishes |
| `requires(id, target)` | exogenous | sensed per node — the pull edge, what this node needs before it can clear |
| `reachable(from, to)` | derived | a path over already-sensed edges |
| `is-leaf(id)` | derived | no `notifies` — structurally the goal or a dead end |

**Actions:**

| Term | Agreed meaning |
|---|---|
| `SENSE(node)` | sense a node's exogenous predicates |
| `WALK(edge)` | move along a connection to a reached node |
| `BACKTRACK` | return along the route |
| `RECORD(belief)` | store a sensed fact as a held belief |
| `REPORT(descriptor)` | return the discovered descriptor |

## Domain: Agent ontology

How the agent loop is defined.

| Term | Agreed meaning |
|---|---|
| `PEAS` | the agent-design frame — Performance, Environment, Actuators, Sensors |
| `Percept` | an input the agent receives from the environment |
| `Agent function` | maps any percept sequence to an action — the ideal behaviour, `f: P* → A` |
| `known(id)` | the agent has heard of this id |
| `visited(id)` | the agent has been there |
| `cleared(id)` | the node's requirements are met |

## Domain: Belief

What the agent holds across both ontologies.

| Term | Agreed meaning |
|---|---|
| **Justified true belief** | a fact the agent holds, with a justification for holding it |
| **Belief state** | the discovered subgraph of the world the agent has walked — the epistemic record |
| **SENSE → RECORD** | the acquisition half — sense the world's exogenous predicates and record them as held beliefs |

*This domain extends with the managing-belief-state work (IA 14, in draft); the terms above are the agreed core.*

## Domain: Trust *(developing)*

*Not yet populated.* The next domain — how the agent relies on a source (a sensor, and the world it reports). Freshness is its first expression. Terms will be agreed as the domain develops.

## The Kinds

Every predicate's truth is determined one of four ways — the classification the ontology uses to say *who determines the atom's truth*:

| Kind | Definition | Example |
|---|---|---|
| **controllable** | the effector's successful return entails the fact — determined by the agent's own action | `known`, `visited`, `cleared` |
| **exogenous** | the effector's successful return does not entail it — the world can change the fact after the action returns | `node`, `notifies`, `requires` |
| **static** | true at setup, never changed by any action or sensing | `domain` |
| **derived** | computed by the state model, never asserted — entailed from other predicates | `reachable`, `is-leaf` |

## Re-entry stays open

A living document. When a later post names a term with no agreed meaning here — or two docs use the same word for different things — the language is re-entered. Normal and expected, not a process violation.
