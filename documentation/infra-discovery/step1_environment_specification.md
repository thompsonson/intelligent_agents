# Infra Discovery: Environment Specification (Step 1 — PEAS)

**Retrofit note:** previously a stub. Filled in from `atomicguard`'s
`platform_topology_peas_and_cli_actions.md` §1–5 — checked directly against
that document, not reconstructed from memory. Per the correction that
prompted this: the hard part (three per-domain PEAS tables, a full CLI
action catalogue) already existed on `atomicguard` PR #369; this file is
the combining synthesis those ingredients were missing, not fresh design
work. Does **not** repeat [`step2_environment_analysis.md`](step2_environment_analysis.md)'s
environment-properties classification (Known/Unknown, Observable,
Static/Dynamic, ...) — that's Step 2's job, already done well there; this
file states the four PEAS elements only.

## Why one combined statement, not three per-domain ones

`platform_topology_peas_and_cli_actions.md` gives real, checked PEAS
analyses — but **per domain**: one table each for `github_actions`,
`kubernetes`, `gcp`. This track's agent is not "an agent sensing GitHub" or
"an agent sensing Kubernetes" — it's one Infra Discovery Agent whose
`NodeId` spans all three domains via the compound `(domain, kind, id)` key.
The three per-domain tables are ingredients; this section is the statement
nothing had combined them into yet.

## Performance, Environment, Actuators, Sensors

| Element | Description |
|---|---|
| **Performance measure** | Correct answer to `Ψ` about infrastructure spanning any combination of `github_actions`/`kubernetes`/`gcp`, returned within `r_patience`/`r_max` and (once decided) `IN-SCOPE`'s budget, with provenance (run URLs, SHAs, resource names) sufficient for a human to act without re-deriving it. Where a `gcp`-hosted resource hands off to Kubernetes, correctly attributing failure to the specific node in the chain, not just "the GCP side" or "the K8s side" generically. **Checked against §3, this is genuinely new synthesis, not a direct inheritance as an earlier version of this row claimed:** §3's own Performance measure caveat ("for GKE-backed resources, correctly handing off to the Kubernetes PEAS above rather than duplicating it") is an instruction about how *this document* should be authored - don't re-derive K8s's own PEAS when covering GKE-hosted resources - not a runtime failure-attribution requirement. The failure-attribution claim above is a reasonable extension of that scoping note, but it's an extension, made explicit here rather than left mischaracterized as something §3 already said. |
| **Environment** | The union of the three per-domain Environments (§1–3): a GitHub repo's `.github/workflows/`, run history, PRs, and dispatch targets; a K8s namespace's Deployments/ReplicaSets/Pods/Services/Ingresses/ConfigMaps/Secrets/Argo Rollouts; a GCP project's GKE clusters/Cloud Run services/Cloud Build triggers/Cloud Functions — connected via the `applies-to` bridge (the only one currently grounded) and the named-but-ungrounded verbs once evidence exists for them. **Where this genuinely isn't just the union:** bounding. §1's GitHub environment is bounded by a single domain's `max_depth`/`max_width` on its own dispatch graph; this combined environment is bounded by `Ψ`/`IN-SCOPE` across the *whole* compound, cross-domain graph — a strictly harder bounding problem than any one domain's own statement poses, and the one place this section isn't reducible to "read the three tables together." |
| **Actuators** | `gh`/`kubectl`/`gcloud` CLI invocations, dispatched via `DSA-CATALOGUE[(domain, kind)]` ([`step0_schema.md`](step0_schema.md)) rather than restated per domain here — the catalogue *is* the actuator inventory; §5's per-domain tables are its source of truth, not a parallel statement to keep in sync. |
| **Sensors** | The same three CLIs' structured (`--json`/`-o json`) and unstructured (exit codes, `kubectl logs`/`get events` text) output, unified under the `Facet{value, observed_at, sensed_by}` accumulation model ([`step0_schema.md`](step0_schema.md)) rather than three separate percept shapes. This is the one row where Step 0's existence does most of Step 1's work already — worth stating as a real efficiency the original sizing exercise found, not a gap. |

## Percepts, combined

Each per-domain PEAS section states its own percept inventory; combined here
rather than re-derived:

- **GitHub** (§1): run status/conclusion, workflow YAML content, PR
  review/check-rollup state, dispatch event payloads.
- **Kubernetes** (§2): `status.availableReplicas` vs. `status.replicas`, Pod
  `phase`/`conditions`, container `ready`/`restartCount`, event stream
  (`reason`, `lastTimestamp`), endpoint address count.
- **gcloud/GCP** (§3): resource `status`/`state` fields (naming varies by
  service — Cloud Run: `status.conditions[Ready]`; GKE: `status=RUNNING`;
  Cloud Build: `status=SUCCESS`), IAM/quota errors surfaced as non-zero exit
  + stderr.
- **Cross-domain, not reducible to any one domain's list** (§4): credential
  context state (`gh` auth → `gcloud` auth → in-cluster `kubectl` context
  via `gcloud container clusters get-credentials`) is itself a percept /
  precondition a bridge-crossing DSA needs to check before generating the
  next domain's command — a stale or missing `kubectl` context fails
  silently different from a resource genuinely being absent, per §4's own
  wording.

## What's still genuinely open here, not resolved by combining the tables

- **gcloud's Known/Unknown status is provisional**, per §3's own note: "the
  least-developed domain in the repo's catalogue... any PEAS claim here is
  provisional until the discovery/AP catalogue work in §5 is done." This
  combined statement inherits that caveat for the `gcp` third of the
  Environment row; not resolved by this document.
- **The bounding claim** ("`Ψ`/`IN-SCOPE` across the whole compound graph")
  states the shape of the problem, not a solution — `IN-SCOPE(subject, Ψ)`
  boundedness (`OQ-007`) is exactly as open here as it is everywhere else in
  this track.

## Related documents

- [`step2_environment_analysis.md`](step2_environment_analysis.md) — Step 2 (environment properties); deliberately not duplicated above.
- [`step0_schema.md`](step0_schema.md) / [`step0_ubiquitous_language.md`](step0_ubiquitous_language.md) — Step 0; the vocabulary this file's Actuators/Sensors rows point to rather than restate.
- `atomicguard`'s `docs/design/notes/platform_topology_peas_and_cli_actions.md` — §1–3 (per-domain PEAS), §4 (cross-domain composite PEAS / credential handoff), §5 (CLI Action Catalogue) — the direct source for every row above.
- [`open_questions.md`](open_questions.md) — `OQ-007` (`IN-SCOPE` boundedness), the open item this file's bounding claim depends on.
