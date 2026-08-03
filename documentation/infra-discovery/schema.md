# Infra Discovery: Ontology Schema

## Purpose

`environment_design.md` sketched `NodeId`/`Facet`/`Edge` as signatures only, deliberately not a full reference - the point there was showing *why* the shape has to change from `real_discovery/`'s, not pinning down every field. This document is that reference: the actual field-level schema, and - just as load-bearing - the actual registered vocabulary (which `domain`s, which `kind`s per domain, which `edge_type`s) this environment would validate against. That vocabulary isn't invented here; it's reused verbatim from `atomicguard`'s own `DSA-CATALOGUE`/`BRIDGE-CATALOGUE` content (`platform_topology_peas_and_cli_actions.md` §5, `topology_sensing_dsa_belief_state_and_agent_function.md`'s Step 3), the same discipline every other document in this track has followed - checked against the real source, not reconstructed from memory.

No code exists yet. This is schema-as-documentation, not a Python module - types are written in dataclass-like pseudocode for precision, the same register `environment_design.md` already used.

## `NodeId`

```python
@dataclass(frozen=True)
class NodeId:
    domain: str   # which handler owns it - closed, registered set, see "Domains and kinds" below
    kind: str     # closed type within that domain - declared by the domain, not global
    id: str       # unique only within (domain, kind) - not globally unique
```

**Constraints**, stated explicitly since none of these are enforced by the tuple shape alone:
- `domain` must be a key in the registered `DSA-CATALOGUE` (see below) - an unregistered domain isn't a different kind of node, it's not sensable at all, since nothing would exist in `legal_actions` for it.
- `kind` must be registered under that `domain`.
- `id`'s format is domain/kind-specific (a GitHub `job` id is numeric; a Kubernetes `Pod` id is a DNS-1123 name within a namespace) - this schema doesn't standardize it, matching the source ontology's own choice not to.

## `Facet`

```python
@dataclass(frozen=True)
class Facet:
    value: Any
    observed_at: datetime
    sensed_by: str   # which DSA produced this facet - a key into DSA-CATALOGUE's entries, not a free-text label
```

A node's `state` (as `belief_state` holds it, not a field any class carries - see "Where a node's state actually lives," below) is `Dict[str, Facet]`, keyed by facet name (`"rollout"`, `"replica_readiness"`, `"conclusion"`) - domain/kind-specific vocabulary again, not standardized across kinds. Two facets for the same `(domain, kind, id)` can have different `sensed_by` and wildly different `observed_at` - that's the point of the shape, not an edge case.

## `Edge`

```python
@dataclass(frozen=True)
class Edge:
    from_: NodeId
    to: NodeId
    edge_type: str    # domain-native verb, or one of the fixed cross-domain bridge verbs - see below
    evidence: str      # what artifact/observation produced this claim
```

**Open, not schematized here** (inherited directly from the source ontology document's own unresolved questions, restated in `environment_design.md`): whether `Edge` needs its own `observed_at`/`sensed_by` the way `Facet` does (the "edge statefulness" question), and whether two independent discoveries of what's semantically the same relationship - once from `from`'s artifact, later from `to`'s (see `environment_design.md`'s "Discovery is bidirectional") - should collapse into one `Edge` or be kept as two, timestamped observations of the same claim. This schema doesn't pick an answer; picking one changes whether `Edge` needs an identity field of its own (e.g. a hash of `(from, to, edge_type)` to de-duplicate against) or stays a plain value type.

## Where a node's state actually lives

Worth restating precisely, since it's easy to misread the dataclasses above as "the Node class": **there is no `Node` class this schema defines.** `environment_design.md`'s "Who owns what" resolution (inherited from the source ontology document's own "The DSA invocation *is* the node") means a node is never materialized as an object - it's a `(domain, kind, id)` key into `belief_state`'s own facet map, nothing more. `NodeId` is a real type; "Node" is a *view* over `belief_state`, assembled on read (`belief_state.facets_for(node_id) -> Dict[str, Facet]`), not a value anything constructs or holds.

## Domains and kinds - the registered vocabulary (`DSA-CATALOGUE`)

Reused verbatim from `atomicguard`'s own catalogue (sensing DSAs only, matching the source document's sensing-first scope - acting DSAs are catalogued there too but marked `[deferred]`, not reproduced here since nothing in this schema depends on them yet):

**`github_actions`**

| kind | DSA | wraps |
|---|---|---|
| `workflow_run` | `DSA-GH-RUN-LIST` | `gh run list --repo {repo} --json databaseId,headSha,status,conclusion` |
| `workflow_run` | `DSA-GH-RUN-WATCH` | `gh run watch {run_id} --repo {repo} --exit-status` (blocking) |
| `workflow_file` | `DSA-GH-WORKFLOW-FILE` | `gh api repos/{repo}/contents/.github/workflows/{file}` |
| `pull_request` | `DSA-GH-PR-VIEW` | `gh pr view {pr_number} --json headRefOid,reviewDecision,statusCheckRollup` |
| `job` | `DSA-GH-JOB-WATCH` | `gh api repos/{repo}/actions/jobs/{job_id}` |

**`kubernetes`**

| kind | DSA | wraps |
|---|---|---|
| `Deployment` | `DSA-K8S-DEPLOYMENT-GET` | `kubectl get deployment {name} -n {ns} -o json` |
| `Deployment` | `DSA-K8S-ROLLOUT` | `kubectl rollout status deployment/{name} -n {ns}` (blocking) |
| `Deployment` | `DSA-K8S-PODSET` | `kubectl get pods -n {ns} -l {selector} -o json` |
| `Pod` | `DSA-K8S-POD-STATUS` | `kubectl wait --for=condition=Ready pod/{name} -n {ns}` (blocking) |
| `Pod` | `DSA-K8S-POD-LOGS` | `kubectl logs .../kubectl get events` (diagnostic) |
| `Service` | `DSA-K8S-ENDPOINTS` | `kubectl get service ... then kubectl get endpoints` |
| `Ingress` | `DSA-K8S-INGRESS` | `kubectl get ingress {name} -n {ns} -o json` |
| `ConfigMap` | `DSA-K8S-CONFIGMAP` | `kubectl get configmap {name} -n {ns} -o json` |
| `Secret` | `DSA-K8S-SECRET` | same shape as `DSA-K8S-CONFIGMAP` |

**`argo_rollouts`** - kept separate from `kubernetes`, per the source document's own choice

| kind | DSA | wraps |
|---|---|---|
| `Rollout` | `DSA-ARGO-ROLLOUT` | `kubectl get rollout {name} -n {ns} -o json` |

**`gcp`**

| kind | DSA | wraps |
|---|---|---|
| `GKE_cluster` | `DSA-GCP-CLUSTER` | `gcloud container clusters describe {cluster} --region {region} --format=json` |
| `CloudRun_service` | `DSA-GCP-RUN-SERVICE` | `gcloud run services describe {name} --region {region} --format=json` |
| `CloudBuild_trigger` | `DSA-GCP-BUILD-TRIGGER` | `gcloud builds triggers describe {trigger} --format=json` |
| `CloudFunction` | `DSA-GCP-FUNCTION` | `gcloud functions describe {name} --format=json` |

This table is a snapshot, not this repo's own source of truth - `atomicguard`'s catalogue can grow (new domains, new kinds) without this document being kept in lockstep; anything built against this schema should read the catalogue from there, not hardcode a copy of this table.

## Edge types (`BRIDGE-CATALOGUE`)

Only one bridge type is actually grounded in evidence so far:

```
BRIDGE-CATALOGUE[applies-to] = DSA-CATALOGUE[(target.domain, target.kind)]
```

Evidence pattern: `kubectl apply`/`kubectl set image`/`gcloud run deploy`/`gcloud builds triggers run` found in a `github_actions.job`'s step log, read off content already fetched (`RESOLVE-BRIDGES`, free, no new DSA call).

**Named but not yet grounded** (no evidence pattern documented for any catalogued domain): `exposes`, `triggers`, `publishes-to`, `observed-by`, `selects-from`, `depends-on-external`. Listed here, not silently dropped, because `environment_design.md`'s bidirectional-discovery finding and `examples.md`'s illustrations both use `selects-from` as a worked example of the `edge.from`-is-new case - worth being explicit that this specific verb is illustrative of the *shape* of the problem, not a claim that `selects-from` itself is grounded yet. `BRIDGE-CATALOGUE[edge.edge_type]`'s applicability to a currently-ungrounded verb is undefined until it's grounded, same as `DSA-CATALOGUE` entries for undocumented kinds are.

**Known gap, inherited directly, not new here:** `gcp.GKE_cluster ↔ kubernetes.*` doesn't fit any current bridge verb (a cluster doesn't mutate what it hosts, ruling out `applies-to`; "hosts" isn't in the vocabulary). Same status as it has in the source document - open, not resolved.

## `belief_state`'s schema, sketched

Not designed in full (`environment_design.md`'s own "Not decided" already says so), but sketchable at the operation level, matching the source document's own `AGENT-FUNCTION`/`SWEEP-CLEARED` pseudocode exactly rather than inventing new operation names:

| Operation | Shape | Notes |
|---|---|---|
| `RECORD(subject, artifact)` | `NodeId × Artifact → ()` | Merges whatever facet(s) `artifact` represents into `subject`'s facet map - not a full replace, since prior facets from other DSAs must survive |
| `RECORD-EDGE(edge)` | `Edge → ()` | See "Open, not schematized here," above, for whether this de-duplicates |
| `RECORD-REQUIRES(subject, requires)` | `NodeId × Tuple[NodeId, ...] → ()` | Declared or discovered dependency set - open question 1, `algorithm_fit.md` |
| `RECORD-UNKNOWABLE(dsa, subject)` / `RECORD-BLOCKED(dsa, subject, reason)` | - | Propagates to permanent non-clearance via `SWEEP-CLEARED`, not a separate cycle-detection mechanism (see `atomicguard`'s `07035745`) |
| `cleared` | `Set[NodeId]`, monotonically growing | Maintained by `SWEEP-CLEARED()`'s iterative fixed-point pass, never by per-query recursion - the specific property the `CLEARED` cycle-safety fix depends on |
| `facets_for(subject)` | `NodeId → Dict[str, Facet]` | The read side of `state` - see "Where a node's state actually lives," above |
| `edges_from(subject)` / `edges_to(subject)` | `NodeId → List[Edge]` | Named symmetrically on purpose - `environment_design.md`'s bidirectional finding means both directions need to be queryable, not just one |

## Example instances

Illustrative only - not generated from any running code, since none exists yet. See `examples.md` for these rendered as diagrams, with the bidirectional-discovery case worked through in full.

```json
{
  "node_id": {"domain": "github_actions", "kind": "job", "id": ".../job/deploy-staging"},
  "facets": {
    "conclusion": {"value": "success", "observed_at": "2026-08-03T10:00:00Z", "sensed_by": "DSA-GH-JOB-WATCH"}
  }
}
```

```json
{
  "from": {"domain": "github_actions", "kind": "job", "id": ".../job/deploy-staging"},
  "to": {"domain": "kubernetes", "kind": "Deployment", "id": "staging/web-frontend"},
  "edge_type": "applies-to",
  "evidence": "step: kubectl apply -f deployment.yaml --context staging"
}
```

## Not decided

- **Edge identity/de-duplication** - stated above, inherited from the source ontology document's own open "edge statefulness" question, sharpened by the bidirectional-discovery finding (the same relationship discoverable from either end).
- **Facet value typing** - `Any` above is honest, not a placeholder for something already decided. Different facets have structurally different value shapes (`conclusion` is an enum string; `replica_readiness` is a `{ready, desired}` pair) - whether this schema should type each facet name's value shape per-kind, or stay untyped and push validation into each DSA's own guard, is open.
- **`belief_state`'s actual persistence backend and index** - this table describes operations, not storage. `environment_design.md`'s own "Not decided" already flags this; unchanged here.

## Related documents

- [`environment_design.md`](environment_design.md) - the properties table and node-ownership reasoning this schema is the field-level reference for.
- [`algorithm_fit.md`](algorithm_fit.md) - `SWEEP-CLEARED`, `RECORD-UNKNOWABLE`/`RECORD-BLOCKED` propagation, and why `cleared` has to be iterative, not recursive.
- [`examples.md`](examples.md) - these types and this vocabulary, instantiated and diagrammed.
- `atomicguard`'s `docs/design/notes/platform_topology_peas_and_cli_actions.md` §5 - the real `DSA-CATALOGUE`/CLI action catalogue this document's vocabulary table is reused from verbatim.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - `BRIDGE-CATALOGUE`'s `applies-to` rule and the ontology's own field definitions.
