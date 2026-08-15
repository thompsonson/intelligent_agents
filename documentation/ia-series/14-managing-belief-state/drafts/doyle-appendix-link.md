# Doyle's appendix to the approach — mapping §1.7 to the belief-state thread

*Draft. Supporting note for IA 13/14. Not part of the series. Source: Jon Doyle, "A Model for Deliberation, Action, and Introspection," PhD thesis, MIT, May 1980, AI TR-581.*

## 1. What "the appendix" is

AITR-581 has **no formal appendix** — it is seven chapters. The material that links Doyle's approach to prior art is **§1.7 "Relation to Other Works" (pp. 43–58)**, split into §1.7.1 *Major Influences and History* (the lineage, told first-person) and §1.7.2 *Related Works* (his approach positioned against each prior thread, by topic). Behind §1.7 sit the mechanism chapters the links point at: **§3 Foundations of the Theory of Reasoning** (RMS, states of belief, justifications, defeasible reasons, dialectical argumentation), **§5 Deliberation**, and **§6 Deliberate Changes of Mental Life**.

Doyle himself points to a *real* appendix inside the related-works survey: §1.7.2.5 cites Barnard (1938), "which has an intriguing appendix on the nature of mind and reasoning, logical and non-logical."

## 2. The lineage (§1.7.1)

Doyle's own thread, first-person:

- **1976** — "The use of dependencies in the control of reasoning" — early RMS; the need to control reasoning *about reasoning*.
- **1977** — "Explicit control of reasoning" (de Kleer, Doyle, Steele, Sussman) — AMORD; explicit representation of the control state.
- **1979** — "A Truth Maintenance System" — RMS developed "further along with its philosophy and applications." This is the paper IA 14 already cites for INVALIDATE/contraction.
- The interpreter is **an extension of NASL's task-network interpreter** (McDermott), reorganized around RMS, with a hierarchical plan library, **the separation of desires and intentions**, and reasoned deliberation. NASL's choice protocol is "a simple relative of reasoned deliberation, with little of the structure, power, or intuitiveness of the latter."
- Influences named: Minsky (reflection, affect, critique of the logistic approach), McCarthy's Advice Taker (indirectly, through Sussman), NETL and FOL (SDL's representational ancestors), Weyhrauch, Davis's meta-rules, Hayes (reasoning about control), Rich & Shrobe (plans).

**Anchor for IA 14:** this is the exact lineage our INVALIDATE/reason-maintenance claim derives from — not a generic "truth maintenance," but a specific program that began as a fact-garbage-collector fix in ARS and became a domain-independent subsystem for non-monotonic belief.

## 3. Topic → IA bridge (§1.7.2)

| Doyle §1.7.2 | What he says | Bridge to our thread |
|---|---|---|
| **§1.7.2.2 The Nature of Reasoning** | **Tukey's theory of conclusions** — statements "with very strong evidence can be adopted as conclusions, to be maintained independently of the evidence until and unless very strong evidence to the contrary is accepted." **Lehrer & Paxton** — knowledge as "undefeated justified true belief." | The epistemic-copy claim in embryo: a fact is a justified true belief (IA 13), held independent of the evidence *until contradicted* — which is exactly the held copy that can go stale (IA 14). *Strongest bridge.* |
| **§1.7.2.7 Adaptive Changes of Mind** | Belief revision (surveyed by Doyle & London 1980); **Quine / Quine–Ullian** on the ambiguity of revisions and guidelines for "minimal" revisions; counterfactuals as minimal-change choice. | RESENSE / RECONCILE / INVALIDATE and the freshness axis: revising a belief is underdetermined, so the doctrine's declared bounds are a way of choosing between alternate revisions. |
| **§1.7.2.5 Decision-making + §1.7.2.4 Fragmentation of Values** | Decision-theory's "chauvinistic utility" vs the deliberation literature, which "admits the fragmentation of values, and concentrates on the reasons involved in the deliberation." Arrow's impossibility as the extreme case. | Why the belief state manages *justifications* (Kind) rather than a scalar confidence: there is no single aggregate value. Doyle's reasoned deliberation over reasons is the philosophical grounding for the reserved stochastic-reasoning (confidence) thread. |
| **§1.7.2.3 The Theory of Intentional Action** | Plans as intentions (Miller, Galanter & Pribram); plan-recognition and action-interpretation work. | The action side of the agent function — WALK / RECORD / REPORT are plan-execution as intention, not bare transitions. |
| **§1.7.2.1 Representation Theory** | Self-descriptive / meta-circular systems; his stated aim is to *use* self-reference for control, not merely formalize it ("None tell how to reason about oneself... An aim of this thesis is to explain ways of doing just that"). | The world-ontology / agent-ontology split and self-knowledge: the agent describes aspects of itself in the same language it uses for the world. |
| **§1.7.2.6 Control of Reasoning** | The gap in prior control work: "control depends on a chauvinistic decision-making domain." | The declared-doctrine move: re-sensing becomes ontology-driven (IA 14's freshness axis) rather than a fixed control policy. |

## 4. What Doyle does NOT supply

Doyle gives the **justification + retraction + reasoned-deliberation machinery** — the retraction half of the freshness axis — but **not the temporal staleness bound** (`:fresh-for` / `:stale-on`). His framework is about pedigree, not *when to re-sense*. The temporal side comes from the situation-calculus-with-knowledge line (Scherl & Levesque 1993) and planning-under-uncertainty's re-sensing stance, not from AITR-581. IA 14's attributions should stay on that line: Doyle anchors INVALIDATE and the "justification is what Kind names" claim; he is not the source of the doctrine.

## 5. Notes in lestash

Threads in the personal knowledge base that trace the same reconciliation — what Doyle actually offers vs the rational-agent definitions:

- [14224 — "What does Jon Doyle or Woodbridge and Jennings offer?"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14224) — the thread's opening question (own note).
- [14226 — "I found his PhD paper and ideas for Rational Psychology informative"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14226) — own note.
- [14227 — Doyle positioned against the framework definition](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14227) — first (over-attributed) synthesis: Doyle as decision criteria under resource bounds.
- [14228 — "Jon Doyle really defined the rationality of it?"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14228) — the challenge (own note).
- [14229 — what Doyle actually contributed](https://pop-mini.monkey-ladon.ts.net:8444/api/items/14229) — the correction: architecture of rational thought, not the definition of rational decisions.
- [20881 — "No, I overstated. Doyle worked on reason maintenance and belief revision"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/20881) — the user's own correction; bounded rationality is Simon, not Doyle (own note).
- [20882 — the reframed synthesis](https://pop-mini.monkey-ladon.ts.net:8444/api/items/20882) — Doyle tracked into reason maintenance / belief revision for guard-dependency tracking.
- [2300 — "Definitions — Rational Psychology"](https://pop-mini.monkey-ladon.ts.net:8444/api/items/2300) — the term-sheet artifact (own note).
- [7828 — Russell & Norvig referencing Doyle's Rational Psychology](https://pop-mini.monkey-ladon.ts.net:8444/api/items/7828) — the AIMA citation thread (own note).

The through-line in these notes matches this draft's §4: Doyle supplies the *reason-maintenance / belief-revision machinery*, not the rationality criterion (that's Simon/decision theory).

## 6. Reference note

- Primary source: DSpace@MIT handle `1721.1/6883` (AITR-581), PDF `AITR-581.pdf`. Text verified against the Internet Archive bitsavers copy.
- Mechanism chapters behind the §1.7 links: §3.4 States of Belief, §3.5–3.6 Justifications, §3.11 Defeasible Reasons and Dialectical Argumentation, §5 Deliberation, §6 Deliberate Changes of Mental Life.
- Doyle's own pointer to a real appendix: Barnard (1938), cited in §1.7.2.5 for "an intriguing appendix on the nature of mind and reasoning."
