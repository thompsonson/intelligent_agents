# [IA Series 13/n] The Grammar of Natural Language — A Term Sheet

*This is a term sheet for the grammar of natural language, in the same spirit as the [Intelligent Agents Term Sheet](https://matt.thompson.gr/2025/05/16/ia-series-n-intelligent-agents.html) and the [Grammar of Logic](../logic/blog.md). The core terms come from the standard linguistics literature and Russell and Norvig's 'Artificial Intelligence: A Modern Approach' (Chapter 23).*

## Introduction

My interest in meaning goes back to reading the Thesaurus as a kid — grammar didn't interest me much, but meaning did. The agents in this series are natural-language interfaces: they read prompts and write answers in this language. The grammar of logic (Series 11) is how an agent reasons; the grammar of natural language is how it communicates. The LLM agents I build sit exactly on that bridge, so the language they process deserves the same term-sheet treatment as the logic they reason in. This post is deliberately lean — a shared vocabulary, not a textbook.

## The Grammar — Core Terminology

### Morphology — the shape of words

- **Morpheme**: The smallest unit of meaning. A word is built from morphemes.
  - **Free morpheme**: Stands alone (`run`, `book`).
  - **Bound morpheme**: Attaches to another morpheme (`-s`, `-ed`, `un-`).
- **Inflection**: Modifying a word to fit grammar without changing its core meaning — `walk` → `walked` (tense), `cat` → `cats` (number). It does not create a new word.
- **Derivation**: Building a *new* word — `run` → `runner`, `happy` → `unhappy`. It can change meaning and category.

### Lexical categories (parts of speech)

- **Noun (N)**: Names an entity — `agent`, `pipeline`.
- **Verb (V)**: Names an action or state — `query`, `deploy`.
- **Adjective (Adj)**: Modifies a noun — `observable`, `stochastic`.
- **Adverb (Adv)**: Modifies a verb, adjective, or sentence — `quickly`, `partially`.
- **Determiner (Det)**: Marks a noun phrase — `the`, `a`, `this`.
- **Preposition (P)**: Relates a noun phrase to the rest of the sentence — `in`, `through`, `at`.
- **Pronoun**: Stands in for a noun phrase — `it`, `they`.
- **Conjunction**: Joins constituents — `and`, `or`, `if`.

### Phrases and sentences

- **Phrase**: A group of words functioning as a unit. Named by its head — **noun phrase (NP)**, **verb phrase (VP)**, **prepositional phrase (PP)**.
- **Constituent**: A word or group of words that behaves as a single unit in the grammar.
- **Clause**: A phrase built around a verb. **Independent** clauses stand alone as sentences; **dependent** clauses do not.
- **Sentence (S)**: An independent clause — a complete unit of the grammar.
- **Parsing**: Recovering a sentence's grammatical structure from its word string.

### Grammatical functions

- **Subject**: The noun phrase a sentence is about; typically the agent of the action.
- **Object**: The noun phrase the action is directed at.
- **Predicate**: What the sentence says about the subject — the verb and its dependents.
- **Agreement**: Grammatical matching between constituents — subject and verb agree in number (`the gate is` vs `the gates are`).
- **Case**: The grammatical role of a noun phrase — `I` (subject) vs `me` (object).
- **Tense**: When the event occurs — past, present, future.
- **Aspect**: How the event unfolds in time — progressive, perfective.
- **Mood**: The speaker's attitude to the event — indicative, imperative, subjunctive.
- **Voice**: How the action relates to its participants — active (`the agent queries`), passive (`is queried`).
- **Word order**: The ordering of subject, verb, and object — English is SVO.

## The Grammar, stated

The standard first approximation is a **context-free grammar** of phrase-structure rules:

```
S  → NP VP
NP → Det N | Det Adj N | Pronoun | ProperNoun
VP → V NP | V NP PP | V AdvP
PP → P NP
```

A caveat worth naming: natural language is *not* fully context-free — agreement, case, and dependencies leak across the boundaries this grammar draws. The CFG is the workable approximation, not the whole truth.

## Semantics — Meaning

- **Reference**: What an expression points at in the world — `the merge gate` refers to a particular object.
- **Sense**: The meaning of an expression independent of what it points at — `the morning star` and `the evening star` differ in sense but share a reference.
- **Compositionality**: The meaning of a whole is a function of the meanings of its parts (Frege's principle).
- **Semantic roles**: The parts participants play in an event — **agent** (does it), **theme** (undergoes it), **instrument** (does it with), **recipient** (receives it).
- **Lexical semantics**: Word meaning, organized into relations — **synonymy** (same meaning), **antonymy** (opposite), **hyponymy** (kind-of: *deployment* is a hyponym of *action*), **meronymy** (part-of), **polysemy** (one word, related senses: *gate* = the physical object or the decision), **homonymy** (one word, unrelated senses: *bank*).
- **Distributional semantics**: The view that meaning is *determined by distribution* — a word's meaning is fixed by the contexts in which it occurs. The [distributional hypothesis](https://en.wikipedia.org/wiki/Distributional_semantics#Distributional_hypothesis) is due to [Harris (1954)](https://doi.org/10.1080/00437956.1954.11659520); [Firth (1957)](https://en.wikipedia.org/wiki/Distributional_semantics) gave its slogan: *"a word is characterized by the company it keeps."* Meaning is quantified as vectors over co-occurrence ([LSA](https://en.wikipedia.org/wiki/Latent_semantic_analysis), [word2vec](https://en.wikipedia.org/wiki/Word2vec)) — the basis of modern LLM semantics, and the natural-language counterpart of the logic sheet's Determination: where logic's truth is *attributed* by a human-chosen model, natural-language meaning is *determined* by the distribution of the corpus — learned from usage, not attributed.
- **Compositional distributional semantics**: Merging the grammar's compositionality with distributional vectors, so the meaning of a phrase is computed from the meanings of its parts ([Clark, Coecke & Sadrzadeh 2008](http://www.cs.ox.ac.uk/people/stephen.clark/papers/qai08.pdf)). The same family as [distributed representations (Rieger 1991)](http://ftp.icsi.berkeley.edu/ftp/pub/techreports/1991/tr-91-012.pdf), where meaning lives spread across many dimensions rather than in one place.
- **Ambiguity**: A phrase with more than one meaning.
  - **Lexical**: a word has multiple senses.
  - **Structural**: the grammar permits two structures — *"the agent sees the man with the telescope"* attaches the PP to the object or the verb.
- **Truth conditions**: The conditions under which a sentence is true. This is where natural-language meaning meets the logic term sheet: a sentence's truth conditions are *determined* by the grammar and *attributed* by the reader, exactly as the logic sheet's Determination defines.
- **Anaphora**: A word that refers back to an earlier one — *"the agent finished its run; it then merged."*

## Pragmatics — Using the Grammar

- **Pragmatics**: What a speaker *means* by an utterance, beyond what the sentence literally says.
- **Utterance**: A particular use of a sentence in a context.
- **Context**: The situation of the utterance — who speaks, to whom, when, and against what shared background.
- **Speech acts**: What an utterance *does* — **asserting** (`the pipeline is green`), **asking** (`is it green?`), **requesting** (`make it green`), **promising**.
- **Implicature**: What is communicated beyond what is said — *"the gate is open"* can imply "you may go," without stating it.
- **Presupposition**: What an utterance takes for granted — *"the merge failed"* presupposes a merge existed.
- **Deixis**: Meaning that depends on the context of utterance — *I*, *you*, *here*, *now*, *this*.
- **Discourse**: A sequence of utterances — the level above the sentence, where anaphora, coherence, and topic live.

## Closing

Logic is how the agent reasons; natural language is how it communicates; the ubiquitous language of the ontology work is the shared vocabulary expressed in this grammar. The LLM sits on that bridge — parsing the natural language into meaning, and generating natural language that carries it back. This term sheet names the pieces of that interface so the series can describe it precisely.
