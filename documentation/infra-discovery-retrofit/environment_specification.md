# Infra Discovery: Environment Specification (Step 1 - PEAS)

**Status: Stub.** This is a sizing finding, not a placeholder waiting for
content that was simply misfiled elsewhere. Checked directly against the
original `environment_design.md` (`documentation/infra-discovery/`): it
contains a full Step 2 properties table, ontology signatures, decisions, and
findings - but no Performance/Environment/Actuators/Sensors table, and no
percept/action inventory. Step 1, for this specific track, was never
written.

## What exists instead

`atomicguard`'s `docs/design/notes/platform_topology_peas_and_cli_actions.md`
gives real, checked PEAS analyses - but **per domain**: one table each for
`github_actions`, `kubernetes`, `gcp`. Each is genuinely useful and already
cited throughout this track's other documents (the Single/Multi-agent row in
`environment_analysis.md` defers to it directly).

What doesn't exist anywhere is a PEAS table **at the level this track is
actually designing an agent for** - not "an agent sensing GitHub" or "an
agent sensing Kubernetes," but one Infra Discovery Agent whose `NodeId`
spans all three domains via the compound `(domain, kind, id)` key. The
three per-domain tables are ingredients; nothing has combined them into the
single Performance/Environment/Actuators/Sensors statement Step 1 is
supposed to produce for *this* agent.

## What writing this file for real would need to state

Sized, not drafted - producing this is real synthesis work, not a copy or a
mechanical split, unlike most of this retrofit:

- **Performance** - a cross-domain formulation. The three per-domain tables
  each state performance in domain-specific terms (correct rollout verdict
  for K8s, correct topology verdict for GitHub); Step 1 needs one statement
  that covers "correctly answered `Ψ` about infrastructure spanning any
  combination of these domains," not three separate ones.
- **Environment** - the union of the three per-domain Environment rows,
  plus the cross-domain composite PEAS section `platform_topology_peas_and_cli_actions.md`
  §4 already sketches (credential handoff at each bridge) - that section is
  the closest existing thing to owned Step 1 content for this track, and is
  currently only cited, never absorbed into a table here.
- **Actuators** - `gh`/`kubectl`/`gcloud` CLI invocations, unified under
  `DSA-CATALOGUE`'s dispatch rather than restated per domain.
- **Sensors** - the same CLI JSON output, unified under the `Facet`
  accumulation model `schema.md` (Step 0) already defines - this is the one
  row where Step 0's existence actually does most of Step 1's work already,
  worth noting as a real efficiency the retrofit surfaced, not just cost.

## Related documents

- [`environment_analysis.md`](environment_analysis.md) - Step 2; written, unlike this file.
- [`schema.md`](schema.md) / [`ubiquitous_language.md`](ubiquitous_language.md) - Step 0; the vocabulary a real Step 1 write-up would use.
- `atomicguard`'s `docs/design/notes/platform_topology_peas_and_cli_actions.md` - the three per-domain PEAS tables this file's synthesis would draw from; §4's "cross-domain composite PEAS" section is the closest existing precedent.
- `RETROFIT_SIZING.md` - this stub counted as net-new work, not a mechanical move, in the overall sizing.
