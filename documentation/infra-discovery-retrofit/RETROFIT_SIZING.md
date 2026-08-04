# Infra Discovery: Retrofit Sizing

**What this is:** a full trial retrofit of `documentation/infra-discovery/`
into the one-file-per-step + consolidated-register-file structure proposed
in [`agent_design_process_extensions.md`](https://github.com/thompsonson/atomicguard/blob/claude/platform-topology-agent-eduh7h/docs/design/notes/agent_design_process_extensions.md)
(atomicguard PR #369), built in this sibling folder so the original track
stays untouched as a reference baseline - **`documentation/infra-discovery/`
is unmodified by this exercise.** This document is the actual sizing
answer: not an estimate written in the abstract, but what doing it for real
on one track turned up.

**Update, after Steps 1 and 3 were filled in:** the "Verdict" and "Two of
five steps have no owned content" framing below were written when both
files were stubs, and characterized producing their real content as
"unscoped synthesis work." That characterization was too strong, corrected
directly rather than silently: checked against `atomicguard` PR #369, the
actual hard content for both steps already existed there in detail - the
full `AGENT-FUNCTION` pseudocode for Step 3, three per-domain PEAS tables
plus a full CLI action catalogue for Step 1 - and `step0_ubiquitous_language.md`
(already in this retrofit before either stub was filled) already cited
every `AGENT-FUNCTION` component as `Settled in: revision doc`. Writing both
files turned out to be substantially a translation/combination pass, not
fresh design work - true for Step 3 especially (the pseudocode was complete
and only needed reproducing in this track's own vocabulary); Step 1 needed
real, if bounded, synthesis (combining three tables into one PEAS statement
- no such combined statement existed anywhere before this file). The
sections below are left as written at the time, not rewritten, so the
correction is visible rather than absorbed silently - see each stub's own
file for what's actually there now.

## File mapping

| Original file | Became | Kind of work |
|---|---|---|
| `environment_design.md` | `step2_environment_analysis.md` (Step 2) | Extraction - properties table and ontology-adjacent analysis kept; "Nodes and edges, translated" dropped (superseded by `step0_schema.md`); "Discovery is bidirectional" moved to `findings.md`; "Resolved design questions" moved to `decisions.md`; "Not decided" moved to `open_questions.md` |
| *(none)* | `step1_environment_specification.md` (Step 1) | Originally net-new/stub; now filled - synthesis of `atomicguard`'s three per-domain PEAS tables + CLI catalogue into one cross-domain PEAS statement. See the update note above |
| `algorithm_fit.md` | `step4_algorithm_fit.md` (Step 4) | Extraction only - `CLEARED` finding moved to `findings.md`, "Open, not resolved" moved to `open_questions.md`; everything else unchanged, already correctly filed |
| *(none)* | `step3_agent_function.md` (Step 3) | Originally net-new/stub; now filled - the `AGENT-FUNCTION` pseudocode translated from `atomicguard`'s revision document into this track's own file. See the update note above |
| `roadmap.md` | `step5_agent_program.md` (Step 5) | Rename + extraction - "Testing discipline" moved to `decisions.md`; "Step 0" and "Not decided" moved to `open_questions.md` |
| `schema.md` | `step0_schema.md` (Step 0) | Copy, cross-links updated for the rename - content otherwise unchanged |
| `ubiquitous_language.md` | `step0_ubiquitous_language.md` (Step 0) | Copy, cross-links updated for the rename - content otherwise unchanged |
| `examples.md` | `examples.md` | Copy, cross-links updated - **no home in the scheme; see "Left unresolved," below** |
| *(scattered across 5 files)* | `decisions.md` | Consolidation - 4 entries |
| *(scattered across 2 files)* | `findings.md` | Consolidation - 2 entries, both already resolved |
| *(scattered across 5 files)* | `open_questions.md` | Consolidation - 19 entries (14 from the original pass; `OQ-015`/`OQ-016` added on a second review pass, found missing; `OQ-017`-`OQ-019` added on a third pass, checking `step3_agent_function.md`'s reproduced pseudocode against the real source line by line - see below) |
| *(none)* | `blue_sky.md` | **Not created** - see below |

6 files became 11 (12 counting this sizing document itself, which isn't
part of the retrofit's own output). An earlier version of this document
miscounted this as 10 - corrected on review; see "Errors found on review,"
below.

## What sizing this for real found, that estimating it wouldn't have

**Two of five steps had no owned content anywhere in this track - not a
filing problem, but not "unscoped synthesis work" either, as first
characterized here (see the update note at the top).** `step1_environment_specification.md`
(Step 1) and `step3_agent_function.md` (Step 3) were stubs, not because
content was misfiled elsewhere and needed moving, but because nothing in
this track's own files translated it - it lived only in `atomicguard`,
cited by name repeatedly. That's a real finding, and it's real work to fix,
but "unscoped" overstated it: the hard part (the actual pseudocode for Step
3; three real PEAS tables and a full CLI catalogue for Step 1) was already
done, on `atomicguard` PR #369, before either file was written. Filling both
in turned out to be bounded - translation for Step 3, combination for Step
1 - not open-ended design work.

**Consolidating the register files surfaced duplication invisible while
scattered.** `belief_state`'s persistence backend was asked as an open
question independently in three separate documents
(`environment_design.md`, `algorithm_fit.md`, `schema.md`), none
referencing the other two. Edge identity/de-duplication was asked
independently in two. Nothing caught this while each lived at the bottom of
its own document's "Not decided" section - `open_questions.md` catching it
on the first consolidation pass is a real, concrete argument for the
file-based scheme over the tag-in-place alternative considered earlier,
not just a claim made in the design conversation.

**`roadmap.md`'s "Step 0: two decisions" section was mislabeled - a live
instance of the exact problem the whole proposal exists to fix, found
inside our own track while sizing it, not hypothesized.** Checked directly:
neither of the two items it names (`belief_state`'s implementation
strategy; `Edge`'s shape) is actually resolved in the source text - both
are posed as forks with tradeoffs. Under the new scheme these are `OQ-010`
and `OQ-011` in `open_questions.md`, not entries in `decisions.md`.

**`blue_sky.md` doesn't get created - this track has none of its own.**
Every "blue-sky" idea relevant to this work (`RECORD-UNCATALOGUED`, `Edge`
as accumulated `Facet` evidence, `IN-SCOPE` as a consumable budget, ...)
lives in `atomicguard`'s "Blue-sky extensions worth writing down" section,
referenced repeatedly but not owned here either - the same import-by-
reference pattern as Steps 1 and 3, just for a register file instead of a
step file. Worth naming as a pattern, not three unrelated gaps: this track
leans on `atomicguard`'s documents more heavily than its own file structure
currently shows.

## Left unresolved

**`examples.md` doesn't fit the scheme.** Copied unchanged because there's
nowhere better to put it - it's not a Decision, Finding, Open question, or
Blue-sky item, and calling worked examples "Analysis" (the catch-all)
undersells what they do (validate the ontology against a concrete
instance). This is a gap in the proposal itself, already flagged on the
`agent_design_process_extensions.md` side; sizing this retrofit didn't
resolve it, just confirmed it's a real, not theoretical, gap.

**Step 0's file count** - `step0_schema.md` + `step0_ubiquitous_language.md` stayed two
files, per the proposal's own "Not decided" item on this - not resolved
here.

**Whether register files are self-contained per track or need cross-checking
against `atomicguard`'s own decisions/findings/blue-sky content** - this
retrofit only consolidated what was already in `documentation/infra-discovery/`'s
six files. `D1`-`D4`, and the "Blue-sky extensions" section, live entirely
on the `atomicguard` side and aren't duplicated into this track's
`decisions.md`/`blue_sky.md` - referenced by name where relevant, not
copied. Whether that's the right boundary, or whether a track's register
files should absorb everything relevant regardless of which repo it was
decided in, isn't decided here either.

## Errors found on review

A second pass, checking this exercise's own output rather than trusting
the first pass, found four real mistakes - listed here rather than
silently corrected, since a sizing document that hides its own errors
undermines the case it's making for consolidation in the first place:

1. **This document's own file count was wrong.** "6 files became 10" -
   actually 11 (12 counting this document). The Verdict below undercounted
   the mechanical bucket by one for the same reason (7, not the correct 8).
2. **A promise made in three places, kept in none.** `findings.md`,
   `examples.md`, and this track's `algorithm_fit.md` each stated that the
   `ReplicaSet`/unregistered-`kind` gap "is tracked in `open_questions.md`"
   - it wasn't. Added as `OQ-015`.
3. **A referenced-but-never-filed open question.** `decisions.md`'s `D-003`
   and `step2_environment_analysis.md` (twice) both say acting-DSA
   selection "stays open" without it ever getting its own entry. Added as
   `OQ-016`.
4. **A misattributed cross-reference — and this entry itself needed a
   correction.** The *original stub* version of `step3_agent_function.md`
   cited "`algorithm_fit.md`'s Mermaid sequence diagrams" as a model to
   follow - this track's own `algorithm_fit.md` has no Mermaid content; the
   actual diagrams are in `../discovery/atomicguard-bridge/algorithm_fit.md`,
   a different file in a different track. That claim predates the retrofit.
   It did **not**, however, carry forward into this pass to fix: by the time
   this review ran, `step3_agent_function.md` had already been fully
   rewritten (filling the stub with real content) and the rewrite never
   reproduced the bad citation - checked directly, no "Mermaid" reference
   exists anywhere in the current file. The first version of this entry
   claimed the fix happened "in this pass"; it didn't need to, the earlier
   rewrite had already made it moot. Left as a corrected entry rather than
   deleted, since the original claim was real (in the stub, at the time),
   just no longer live by the time anyone went looking for it.

Items 1-3 are fixed in this pass; item 4 turned out to already be resolved
by the time of this review, not by this review - corrected above rather
than silently removed, since a section about catching your own errors
shouldn't itself misdescribe one.

## Gaps found checking the filled Steps 1/3 against their real source

A third review pass, after Steps 1 and 3 were filled with real content:
checked `step3_agent_function.md`'s reproduced `AGENT-FUNCTION` pseudocode
against `atomicguard`'s actual source line by line, rather than trusting
that a faithful-looking reproduction was a complete one. It wasn't -
`step3_agent_function.md`'s translation correctly reproduced the
pseudocode's *logic* (every function, every operator, checked) but silently
dropped two pieces of the source's own inline commentary that name real,
still-open risks, not just explanatory color:

1. **The reachability risk is not auto-solved** - the real source states
   plainly that a `requires` target named in some DSA's `REQUIRES-OF`
   output but never independently discovered via `RESOLVE-BRIDGES`/
   `DSA-CATALOGUE` dispatch "would deadlock silently, and nothing here
   currently prevents that." This track inherits the identical exposure
   and had nothing saying so. Added as `OQ-017`, with a pointer added at
   the exact pseudocode line in `step3_agent_function.md`.
2. **Whether `requires`/`cleared` should ever gate sensing, not just
   acting** - the source names `ELIGIBLE`'s current policy (sensing always
   eligible) as a default, not a settled fact, and states the sensing case
   as deferred, not ruled out. Added as `OQ-018`, same pointer treatment.

A third, lower-stakes item (`OQ-019`, where this agent's code eventually
lands - `atomicguard`, `intelligent_agents`, or a new repo) was also named
explicitly in the source's own "Still open" section and had no home here
either.

Worth stating plainly: a translation pass that reproduces logic correctly
but drops the source's own named risks is a different, subtler kind of
incompleteness than the four errors above - nothing was factually wrong,
the omission just wasn't visible without checking the reproduction against
its source rather than checking it for internal consistency alone.

## Verdict

**Updated three times** after the original pass: once when Steps 1 and 3
were filled (see the note at the top - both turned out to be translation
work sourced from content that already existed on `atomicguard` PR #369,
not fresh design); once after a second, skeptical review pass over this
document's own output caught four further mistakes, listed in "Errors
found on review," above - including this section's own file count, which
was wrong; and once after a third pass checked the filled Steps 1/3
against their real source rather than just for internal consistency,
finding two dropped-but-real risks named in the source and never carried
over (`OQ-017`/`OQ-018`, "Gaps found checking the filled Steps 1/3 against
their real source," above).

Of 11 resulting files: **2 required real, track-owned translation work**
(`step1_environment_specification.md` - combining three per-domain PEAS
tables and a CLI catalogue into one cross-domain statement;
`step3_agent_function.md` - reproducing already-complete pseudocode in this
track's own vocabulary, complete on its logic but initially incomplete on
the source's own named risks - see above), **1 is copied unresolved**
(`examples.md` - no home in the scheme), and **8 are mechanical** -
extraction, consolidation, and renaming of content that already existed,
with three concrete corrections surfacing only because the consolidation
forced a side-by-side read (the triple-duplicated `belief_state` question,
the mislabeled "Step 0" section, the `blue_sky.md` non-file), plus the four
further errors caught on the second review pass (this document's original
"10 resulting files" among them) and the two source-fidelity gaps caught
on the third. The register-file consolidation paid for itself on this one
track before any code changed as a result - and needed three further
passes past the first, not just the first, to actually deliver on that:
one to fill in what the original pass wrongly called unscoped synthesis
work, one to catch what the original pass got wrong about itself, and one
to check the filled content against its own source rather than just for
internal consistency.
