# Infra Discovery: Retrofit Sizing

**What this is:** a full trial retrofit of `documentation/infra-discovery/`
into the one-file-per-step + consolidated-register-file structure proposed
in [`agent_design_process_extensions.md`](https://github.com/thompsonson/atomicguard/blob/claude/platform-topology-agent-eduh7h/docs/design/notes/agent_design_process_extensions.md)
(atomicguard PR #369), built in this sibling folder so the original track
stays untouched as a reference baseline - **`documentation/infra-discovery/`
is unmodified by this exercise.** This document is the actual sizing
answer: not an estimate written in the abstract, but what doing it for real
on one track turned up.

## File mapping

| Original file | Became | Kind of work |
|---|---|---|
| `environment_design.md` | `environment_analysis.md` (Step 2) | Extraction - properties table and ontology-adjacent analysis kept; "Nodes and edges, translated" dropped (superseded by `schema.md`); "Discovery is bidirectional" moved to `findings.md`; "Resolved design questions" moved to `decisions.md`; "Not decided" moved to `open_questions.md` |
| *(none)* | `environment_specification.md` (Step 1) | **Net-new.** No owned PEAS content existed for this track - see below |
| `algorithm_fit.md` | `algorithm_fit.md` (Step 4) | Extraction only - `CLEARED` finding moved to `findings.md`, "Open, not resolved" moved to `open_questions.md`; everything else unchanged, already correctly filed |
| *(none)* | `agent_function.md` (Step 3) | **Net-new.** No owned agent-function content existed for this track - see below |
| `roadmap.md` | `agent_program.md` (Step 5) | Rename + extraction - "Testing discipline" moved to `decisions.md`; "Step 0" and "Not decided" moved to `open_questions.md` |
| `schema.md` | `schema.md` (Step 0) | Copy, unchanged |
| `ubiquitous_language.md` | `ubiquitous_language.md` (Step 0) | Copy, unchanged |
| `examples.md` | `examples.md` | Copy, unchanged - **no home in the scheme; see "Left unresolved," below** |
| *(scattered across 5 files)* | `decisions.md` | Consolidation - 4 entries |
| *(scattered across 2 files)* | `findings.md` | Consolidation - 2 entries, both already resolved |
| *(scattered across 5 files)* | `open_questions.md` | Consolidation - 14 entries |
| *(none)* | `blue_sky.md` | **Not created** - see below |

6 files became 10 (not 11 - `blue_sky.md` doesn't exist).

## What sizing this for real found, that estimating it wouldn't have

**Two of five steps have no owned content anywhere in this track - not a
filing problem.** `environment_specification.md` (Step 1) and
`agent_function.md` (Step 3) are stubs, not because content was misfiled
elsewhere and needed moving, but because it was checked directly against
the original documents and genuinely doesn't exist for this track. Both
steps' real content lives only in `atomicguard`, cited by name repeatedly
but never translated into this track's own words the way the Node/Edge
ontology was. This is the single biggest sizing finding: **the retrofit is
not just data entry.** Producing real Step 1 and Step 3 content is
unscoped synthesis work, sized in each stub file's own "What writing this
file for real would need to cover" section, not attempted here.

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

**Step 0's file count** - `schema.md` + `ubiquitous_language.md` stayed two
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

## Verdict

Of 10 resulting files: **2 are real new-content work** (`environment_specification.md`,
`agent_function.md` - both stubs stating what's missing, not drafts of the
content itself), **1 is copied unresolved** (`examples.md` - no home in the
scheme), and **7 are mechanical** - extraction, consolidation, and renaming
of content that already existed, with three concrete corrections
surfacing only because the consolidation forced a side-by-side read
(the triple-duplicated `belief_state` question, the mislabeled "Step 0"
section, the `blue_sky.md` non-file). The register-file consolidation paid
for itself on this one track before any code changed as a result.
