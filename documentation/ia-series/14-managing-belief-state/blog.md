# [IA Series 14/n] Managing a Belief State

*Draft. Following on from [Ontologies, Doctrine, and Ubiquitous Language](../13-ontologies/blog.md), which stored a fact as a belief. This post is about what happens after you hold one — and the vocabulary the agent needs the moment the world won't sit still.*

## Defining the belief state

"Belief state" has two meanings in the literature. In AIMA it is the set of possible states consistent with what the agent has perceived — an epistemic record. In POMDP planning it is a probability distribution over states. This post means the AIMA sense: the belief state is what the agent knows, not a distribution over what might be.

Two terms carry the definition.

**Epistemic** — pertaining to knowledge: what an agent holds as known, as distinct from what is the case. The agent's grip on the world is always epistemic — incomplete, possibly stale, possibly false. The world is **ontic**: whatever it actually is, regardless of what the agent holds.

**Belief state** — the agent's epistemic record: the persistent, entity-indexed store of its held copies of world facts, each carrying provenance (when, how, by what it was obtained) and a Kind (who determines its truth). It is not the world it models, not the agent's declared commitments, and not the loop that reads and writes it.

AIMA already names the store: the **knowledge base** — "the set of sentences an agent holds to be true," from the Grammar of Logic term sheet (IA 11). The belief state is the runtime instance of that KB: the KB is the declarative structure, the belief state its held, versioned form.

Managing it has its own literature. **Belief revision** (Alchourrón, Gärdenfors & Makinson 1985) is the theory of how beliefs change — revision, contraction, expansion. **Truth maintenance** (Doyle 1979; de Kleer 1986) holds beliefs with justifications and retracts them when a justification fails — which is the Kind story: justification is what Kind names, retraction is what the freshness axis must make declarative. The planning tradition that assumes a fully-known initial state — HTN planners among them — needs no belief state, because there is nothing uncertain to hold. The unknown world is where it earns its keep.

The gap the rest of this post is about: **the world is ontic; the belief state is epistemic; and the two can drift apart.**

## World ontology and agent ontology

[IA 13 drew the split](../13-ontologies/blog.md): the **world ontology** is the environment the agent navigates and acts in; the **agent ontology** is how the agent loop is defined. The belief state sits at their meeting point.

- **What the agent discovers** — the world's facts (`node`, `notifies`, `requires`) and the declared freshness bounds — is **world ontology**: facts about the environment, exogenous or derived.
- **The belief-state lifecycle** — `known`, `visited`, `cleared`, `stale`, and the management actions — is **agent ontology**: the agent's own epistemic machinery, like the loop itself.

The belief state *holds* world-ontology facts; the agent-ontology lifecycle *manages* them. That is the meeting point — and the reason the gap between the held copy and the world is this post's subject. (The full layer model, including the repository the belief state reads from, is the subject of the next post.)

## Storing was the easy half

The [previous post](../13-ontologies/blog.md) established the acquisition half: a fact is a justified true belief, and storing it as a belief is **SENSE → RECORD** — the agent senses the world's exogenous predicates (`node`, `notifies`, `requires`) and records them into its own controllable ones (`known`, `visited`, `cleared`). The temporal caveat was already there: *a fact was true at the point in time it was sensed, or the action was taken.*

That caveat is the whole problem in miniature. The held belief *was* a fact — true at the moment it was sensed. But it is **exogenous**: its truth is set by the world, and the world can change after the sensing. So between one sense and the next, a belief gained by visiting a node can **drift out of sync with the world state** — not because it was a guess, but because the world it was sensed from won't sit still. The world is what the search moves through; the belief is what the search holds. They are different things, and the gap between them is the subject of this post.

## Two channels

Beliefs arrive through two channels, and the channel decides what can go wrong with them.

| Channel | Source | What can go wrong | Managed by |
|---|---|---|---|
| **Sensed** | the world — a node's `notifies`, `requires` | the copy goes stale | re-sensing (the freshness axis) |
| **Reported** | the model's reasoning — `"FINAL:"` | the reasoning is self-attested | confidence (a different mechanism) |

The sensed channel is the one this post manages: the belief state reasons symbolically (IA 11), and re-sensing keeps its copies in sync with the world.

The reported channel is the boundary: the model reasons stochastically (IA 12), and a self-attested belief cannot be re-sensed against the world — only judged. That judgement is a different kind of management, its own subject; here it marks where the freshness axis stops.

## Kind is justification, not freshness

The post on ontologies classified every predicate by **Kind** — controllable, exogenous, static, derived — which is *who determines the atom's truth*. That is the justification axis.

What it is *not* is the **freshness axis**. Kind says nothing about how current your copy is. An exogenous atom is *ground truth at the moment of sensing* — but the copy can go stale the moment the world moves. Justification and freshness are orthogonal: one is about who makes the fact true, the other about when to re-sense.

Why not just add a predicate, `stale(fact)`? Because of the closed-world assumption. An atom absent from the world model is read as false — so `stale(?fact)` would be *entailed false* for every unasserted atom, which is nonsense. Freshness is a property **of a copy** — when it was sensed, by which effector, with what verdict — not a property of the world. It must be **metadata on the epistemic copy, never an atom**.

## The freshness axis: declared doctrine, recorded metadata

There are three questions hiding inside "freshness," and they don't all have the same answer:

| Question | Answer |
|---|---|
| **Storage** — where does freshness live? | metadata on the epistemic copy, never an atom in the world model |
| **Meaning** — is it ontology or bookkeeping? | a **declared staleness bound** per predicate, carried beside `:kind` in the ontology — the freshness *doctrine* |
| **Policy** — who decides when to re-sense? | the loop executes the declared bound — re-sensing becomes ontology-driven |

The sharp claim is the middle row. A bound like *"`ci-green` is fresh for N minutes"* is itself a fact about the world (how fast it changes) — static or derived — so declaring it in the ontology is world content, not a loop concern. This is IA 13's own framing made concrete: **`:kind` is the justification axis; a staleness bound is the freshness doctrine on the same map.** And D4's "always re-sense" turns out to be the degenerate case — no declared bounds, re-sense everything. The doctrine upgrades it to *"re-sense when the declared bound is hit,"* without touching what an atom is.

One rule the doctrine must handle: **derived predicates inherit freshness.** `reachable`, `is-leaf` (and the earlier post's `cleared`) are computed from base atoms — their staleness is a function of their dependencies', not an independent bound. A derived head's freshness bound is the **minimum** (most conservative) of its body's bounds — if any base belief goes stale, everything derived from it is stale — and stale signals **OR-compose** across the body. A derived head may override its declared bound only when re-sensing the aggregate is cheaper than re-sensing its parts. **Consistency is downstream of sync.**

The whole axis in one line: **the ontology declares how fresh each fact must be; the metadata records how fresh it actually is; the loop reconciles the gap.**

[IA 13 ended by deciding what schema.org carries](../13-ontologies/blog.md): facts and their form, never semantics — no Kind, no preconditions, no derived. The freshness axis inherits the same split. A copy's metadata — when it was sensed, by what, with what verdict — is a fact *about the copy*, and it serialises: the belief state's JSON-LD gains `sensed_at` and `sensed_by`. The declared bound — *ci-green is fresh for five minutes* — is doctrine, and like `:kind` it stays in the semantics layer. Schema.org carries the record; the ontology declares how fresh it must be.

## The management actions

With a declared bound and recorded metadata, the loop's job is reconciliation:

- **RESENSE(id)** — re-query a node when its bound is hit or a signal fires, to detect drift
- **RECONCILE(id)** — compare the recorded belief against the fresh sense and update
- **INVALIDATE(id)** — mark a belief stale without yet knowing the truth

These are belief revision and truth maintenance made operational — the theory named in this post's opening, given verbs. RESENSE is the re-observation that supplies new information, the re-sensing stance of planning under uncertainty; RECONCILE is **belief revision** — accommodating new information, even when it contradicts what is held ([Alchourrón, Gärdenfors & Makinson 1985](https://en.wikipedia.org/wiki/Belief_revision)); INVALIDATE is **contraction** — withdrawing a belief whose justification no longer holds, the retraction a truth-maintenance system performs ([Doyle 1979](https://en.wikipedia.org/wiki/Truth_maintenance_system); [de Kleer 1986](https://en.wikipedia.org/wiki/Assumption-based_truth_maintenance)).

These are the actions the earlier post's "when the ontology is re-entered" predicted: the vocabulary the agent needs the moment the world won't sit still.

### The lifecycle, extended

[IA 13's appendix](../13-ontologies/blog.md) drew the acquisition lifecycle: *unknown → known → visited → cleared or blocked.* Its one revision edge — *blocked → cleared, when requires later clear* — was management without the vocabulary.

```mermaid
stateDiagram-v2
    [*] --> Unknown
    Unknown --> Known : SENSE names it
    Known --> Visited : agent arrives
    Visited --> Cleared : all requires cleared
    Visited --> Blocked : requires unmet
    Blocked --> Cleared : requires later clear
    Cleared --> [*]
```

To it, the freshness axis adds the management overlay:

```mermaid
stateDiagram-v2
    [*] --> Known
    Known --> Stale : bound hit / world moved
    Stale --> Known : RESENSE — reconciled
    Stale --> Invalidated : INVALIDATE
    Invalidated --> [*]
```

The overlay's additions are the management machinery: **Stale** is a held belief whose bound is hit or whose world may have moved; **RESENSE** re-observes it and reconciles the copy; **INVALIDATE** withdraws a belief whose justification no longer holds. The lifecycle no longer only grows — it is kept in sync.

## Discovery-driven belief, formally

The world's facts are fluents — `NodeExists(n, s)`, `Notifies(a, b, s)` — whose truth varies over situations. `sense(n)` is a sensing action; after it, the agent **Knows** what it sensed ([Scherl & Levesque 1993](https://en.wikipedia.org/wiki/Situation_calculus), the knowledge formalism for the situation calculus). The belief state *is* the set of fluents the agent Knows in the current situation — populated by discovery, action by action:

```
Do(sense(n), s)  →  Knows(NodeExists(n), Do(sense(n), s))
                 →  Knows(Notifies(a, b), Do(sense(n), s))
```

The drift falls out of the situations: a fluent sensed at `s₀` can be false at `s′ > s₀` — the world moved between situations. The belief state holds knowledge *about a past situation*; re-sensing updates it to the present. That is the freshness doctrine's role: it names how quickly each fluent can change across situations, declared beside the fluent's Kind. Derived fluents inherit the **minimum** of their bodies' bounds; stale signals **OR-compose**.

The management actions are the loop's re-entry into the situations: **RESENSE** performs `sense(n)` again to bring `Knows` up to the current situation; **RECONCILE** folds the fresh sense into the belief; **INVALIDATE** withdraws a `Knows` whose fluent's truth no longer holds. Belief revision and truth maintenance — expressed as knowledge updated across situations.

## Re-entry stays open

The ontology was re-entered the moment the world wouldn't sit still — that was the signal. And writing this has been managing my own belief state: the last post's claim that the belief state was "the controllable side" was a belief I held, and it went out of sync with the world the moment the atomicguard work pointed out the epistemic copies. Justification is not truth; freshness is not Kind; and the belief I hold about my own work needs the same re-sensing I've been describing.
