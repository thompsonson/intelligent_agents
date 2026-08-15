# Domains of the Intelligent Agents series

*Living document. The shared areas the series' vocabulary is organised into. Definitions and boundaries; the agreed meaning of each term lives in the [ubiquitous language](ubiquitous-language.md).*

*Source of truth: the posts remain authoritative for the domains they establish. This document is the living extract — when a post redraws a domain boundary, update it here so the two don't drift apart silently.*

## The domain set

The domains are the areas of the agent architecture the series names. They are distinct because they fail differently and are managed by different machinery.

| Domain | Scope | What it is | The crux |
|---|---|---|---|
| **World ontology** | the environment | what the agent navigates and acts in | the world's facts, sensed or derived |
| **Agent ontology** | the loop | how the agent is defined | percept, agent function, the agent's own machinery |
| **Belief** | what the agent holds | the epistemic record built across both ontologies | the meeting point |
| **Trust** *(developing)* | how the agent relies on sources | the stance that a source's report stays correct | freshness as trust |

The grammars — the [Grammar of Logic](../11-grammar-of-logic/blog.md) and the [Grammar of Natural Language](../12-grammar-of-natural-language/blog.md) — are the **substrate**, not domains: the languages the domains are written in. They are referenced from the ubiquitous language, not absorbed into it.

## 1. World ontology

The environment the agent navigates and acts in: its entities, predicates, actions, and connections.

**Entities:** `Node`, `Edge`, `Domain`, `Status`.

**Predicates** (classified by Kind in the ubiquitous language):
- exogenous: `node`, `notifies`, `requires`
- derived: `reachable`, `is-leaf`

**Actions:** `SENSE(node)`, `WALK(edge)`, `BACKTRACK`, `RECORD(belief)`, `REPORT(descriptor)`.

**Boundary:** the world is what the agent discovers. Its facts' truth is set by the world, not by the agent. This is where the drift between the held copy and the world lives.

## 2. Agent ontology

How the agent loop is defined — the PEAS framework: the agent's percept, its agent function, and the machinery that reads and writes the belief state.

**Agent machinery:** `known`, `visited`, `cleared` — the agent's beliefs about the world it has sensed (controllable, in the ubiquitous language's Kind terms).

**Boundary:** the agent ontology is the agent's own epistemic machinery — the lifecycle and the management actions — not the world it models.

## 3. Belief

What the agent holds across both ontologies: the epistemic record. The belief state *holds* world-ontology facts while the agent-ontology lifecycle *manages* them — it sits at the meeting point of the two.

**Published terms:** a fact is a justified true belief; the belief state is the discovered subgraph of the world the agent has walked; `SENSE → RECORD` is the acquisition half.

*This domain's vocabulary extends with the managing-belief-state work (IA 14, in draft); the published terms above are the agreed core.*

## 4. Trust *(developing)*

The next domain: how the agent relies on a source (a sensor, and the world it reports). Freshness is the first expression of this — the stance that a source's report stays correct for some interval.

**Not yet populated.** Roadmap only; terms will be agreed as the domain develops.

## The Kinds

The Kind classification cuts across the domains: every predicate's truth is determined one of four ways — **controllable**, **exogenous**, **static**, **derived**. The definitions live in the ubiquitous language; the domains reference them rather than duplicate them.

## Re-entry stays open

A living document. When a later post names a term the domains cannot place, the domain set — not the vocabulary alone — is re-entered. This is a normal loop-back, not a process violation.
