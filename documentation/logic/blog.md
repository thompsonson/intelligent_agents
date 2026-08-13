# [IA Series 11/n] The Grammar of Logic — A Term Sheet

*This is a term sheet for the grammar of logic, in the same spirit as the original [Intelligent Agents Term Sheet](https://matt.thompson.gr/2025/05/16/ia-series-n-intelligent-agents.html). Most terms come from Russell and Norvig's 'Artificial Intelligence: A Modern Approach' (Chapters 7-8) and the standard literature on formal logic.*

## Introduction

The ontology work has kept using a vocabulary I never formally defined — predicates, derived rules, well-formedness — all of it written in the language of logic. Before going further I wanted a term sheet for the *grammar* of that language: what the symbols are, what strings count as well-formed, and what a well-formed formula means. This post is that term sheet. It is deliberately lean; the aim is a shared vocabulary, not a textbook.

## The Grammar — Core Terminology

### The symbols

- **Formal language**: A set of strings built from an alphabet according to formation rules.
- **Alphabet**: The symbols a formal language is built from — logical constants, variables, predicates, functions, and punctuation.
- **Connectives**: The logical constants that combine sentences.
  - **Negation (¬)**: *not* — flips a sentence's truth value.
  - **Conjunction (∧)**: *and* — true only when both sides are true.
  - **Disjunction (∨)**: *or* — true when at least one side is true.
  - **Implication (⇒)**: *if ... then ...* — false only when the antecedent is true and the consequent is false.
  - **Biconditional (⇔)**: *if and only if* — true when both sides agree in truth value.
- **Quantifiers**: The logical constants that range over objects.
  - **Universal (∀)**: *for all*.
  - **Existential (∃)**: *there exists*.
- **Equality (=)**: a predicate asserting two terms denote the same object.
- **Parentheses**: grouping, and the grammar's only punctuation.

### Terms

- **Term**: An expression that refers to an object — a constant, a variable, or a function applied to terms.
  - **Constant symbol**: Names a specific object (e.g., `pr-42`).
  - **Variable symbol**: Ranges over objects (e.g., `x`).
  - **Function symbol**: Maps objects to objects (e.g., `parent(x)`).

### Predicates and sentences

- **Predicate symbol**: A relation over objects. Applied to terms it yields an atomic sentence.
- **Atomic sentence (atom)**: A predicate applied to terms — the smallest well-formed sentence (e.g., `merged(pr-42)`).
- **Compound sentence**: Atoms combined with connectives and quantifiers.
- **Well-formed formula (wff)**: A string that obeys the formation rules — the grammar's definition of a legal sentence.
- **Sentence**: A well-formed formula with no free variables (a closed formula) — a claim that has a definite truth value in a model.

### Scope and binding

- **Scope**: The part of a formula governed by a quantifier.
- **Bound variable**: A variable within the scope of its own quantifier.
- **Free variable**: A variable not bound by any quantifier. A formula with free variables is *open*; it has no definite truth value until the variables are assigned.

## The Grammar, stated

The formation rules, in BNF — this is the grammar of logic proper:

```
Sentence         → AtomicSentence | ComplexSentence
AtomicSentence   → Predicate(Term, ...) | Term = Term
ComplexSentence  → ( Sentence )
                 | ¬ Sentence
                 | Sentence ∧ Sentence
                 | Sentence ∨ Sentence
                 | Sentence ⇒ Sentence
                 | Sentence ⇔ Sentence
                 | Quantifier Variable, ... Sentence
Term             → Function(Term, ...) | Constant | Variable
```

Everything else is not a sentence of the language — no matter how plausible it reads.

## Semantics — Meaning

- **Interpretation**: An assignment of meaning to a language — a domain plus a mapping that names the constants, predicates, and functions in it.
- **Model**: An interpretation that makes a given sentence (or set of sentences) true.
- **Domain (universe)**: The set of objects an interpretation ranges over.
- **Truth value**: True or false — what a sentence receives relative to an interpretation.
- **Truth table**: A complete enumeration of a connective's truth behaviour for all combinations of its arguments.
- **Satisfaction**: A formula is satisfied by an interpretation when it is true in it.
- **Entailment (⊨)**: *KB ⊨ α* — every model of the knowledge base is also a model of α. The semantic notion of logical consequence.
- **Validity**: A sentence true in *every* interpretation (a tautology).
- **Satisfiability**: A sentence true in *some* interpretation.
- **Contingency**: A sentence true in some interpretations and false in others — neither valid nor contradictory.
- **Contradiction (unsatisfiability)**: A sentence true in *no* interpretation.
- **Logical equivalence (≡)**: Two sentences true in exactly the same interpretations.

## Reasoning — Using the Grammar

- **Knowledge base (KB)**: The set of sentences an agent holds to be true.
- **Inference**: Deriving new sentences from existing ones.
- **Derivation (⊢)**: *KB ⊢ α* — α is reachable from the KB by applying inference rules. The syntactic notion of proof.
- **Sound inference**: Never derives a false conclusion — every derived sentence is entailed.
- **Complete inference**: Can derive every entailed sentence.
- **Inference rules**: The grammar's rewrite moves — e.g., **modus ponens** (*if* α ⇒ β *and* α *then* β), **conjunction introduction** (α, β ⊢ α ∧ β), **resolution** (a complete rule for propositional and first-order clauses).
- **Entailment vs derivation**: Entailment (⊨) says what is *true given* the KB; derivation (⊢) says what is *provable from* it.
- **Soundness theorem**: If ⊢ then ⊨ — the proof system never lies.
- **Completeness theorem**: If ⊨ then ⊢ — everything true is provable.
- **Decidability**: Whether a proof procedure is guaranteed to terminate with an answer. Propositional entailment is decidable; first-order entailment is not in general.

## Closing

The grammar is the substrate the world ontology is written in: predicates are atomic sentences, Kinds classify how their truth is determined, and a `derived` predicate is an entailment stated by a rule. This term sheet names the pieces so that work can be described precisely.
