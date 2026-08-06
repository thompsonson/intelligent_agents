# Infrastructure Discovery Agent — Step 1 Implementation

**Date:** 2026-08-05  
**Status:** Complete & Validated  
**Scope:** Per step5_agent_program.md Step 1

## What Was Built

A flat `pending`/`RELEVANT`/`INVOKE` agent loop discovering infrastructure topology via compound `NodeId` and bidirectional edge discovery. Implementation validates three key design claims:

### 1. Compound NodeId (D-001)
- **Type:** `NodeId(domain, kind, id)` — not bare strings
- **Pattern:** `github_actions/job/deploy`, `kubernetes/Deployment/web`, `gcp/CloudRun_service/api`
- **Validation:** ✅ DSA-CATALOGUE lookup by `(domain, kind)` works correctly

```python
node = NodeId("kubernetes", "Deployment", "web")
assert hash(node) == hash(NodeId("kubernetes", "Deployment", "web"))
```

### 2. Facet Accumulation
- **Structure:** `Dict[str, Facet]` per node, keyed by facet name
- **Each facet:** `{value, observed_at, sensed_by}` — independent timestamp + source
- **Pattern:** Multiple DSAs sense the same subject → facets accumulate, not replace
- **Validation:** ✅ Two facets for same node, different timestamps, different sources

```python
state.record(node, {"replicas": Facet(3, ..., "DSA-K8S-DEPLOYMENT-GET")})
state.record(node, {"status": Facet("Progressing", ..., "DSA-K8S-ROLLOUT")})
# Both persist
```

### 3. Bidirectional Edge Discovery (F-001 Fix)
- **The bug:** Original pseudocode only enqueued `edge.to` in `RESOLVE-BRIDGES`
- **The fix:** Now enqueues **both** `edge.to` AND `edge.from_`
- **Pattern:** 
  - Forward: `github_actions/job/deploy --applies-to--> kubernetes/Deployment/web`
  - Reverse: `kubernetes/Deployment/web --deployed-by--> github_actions/job/deploy`
- **Validation:** ✅ Both directions queryable; `edges_to()` and `edges_from()` work

```python
# Register edge from A → B
state.record_edge(Edge(A, B, "applies-to", ...))

# Both queries work:
assert B in [e.to for e in state.edges_from(A)]   # Forward
assert A in [e.from_ for e in state.edges_to(B)]  # Backward (F-001)
```

### 4. Flat Loop Structure
- **No stack, phases, or position state** — just `pending` pool
- **Per-turn:** 
  1. `RELEVANT(dsa_set, subject, Ψ)` — de-duplicate & scope-check
  2. `SELECT-NEXT(eligible)` — arbitrary/insertion order for Step 1
  3. `INVOKE(dsa, subject)` — fresh `DualStateAgent` per call
  4. `RECORD` / `RECORD-EDGE` into `belief_state`
- **Validation:** ✅ Full episode runs to completion in 5 steps

## Integration Test Results

**Scenario:** 3-node fixture topology  
**Time:** ~100ms  
**Result:** ✅ PASS

```
Discovered nodes:     3
Edges discovered:     4
Facets accumulated:   8
```

### Nodes
- `github_actions/job/deploy` → 2 facets
- `kubernetes/Deployment/web` → 3 facets  
- `gcp/CloudRun_service/api` → 3 facets

### Edges (bidirectional)
```
github_actions/job/deploy
  --applies-to--> kubernetes/Deployment/web
  --applies-to--> gcp/CloudRun_service/api

kubernetes/Deployment/web
  --deployed-by--> github_actions/job/deploy

gcp/CloudRun_service/api
  --deployed-by--> github_actions/job/deploy
```

All edges queryable in **both directions** ✅ (F-001 validated)

## Type Safety & Dependency Management

**Problem:** atomicguard not installed in test environment.  
**Solution:** TYPE_CHECKING + lazy import pattern

```python
# Module load: no atomicguard import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from atomicguard.application.action_pair import ActionPair

@dataclass
class DSACatalogueEntry:
    action_pair: "ActionPair"  # String literal type

# Runtime: lazy import in invoke() method only
def invoke(self, dsa_entry, subject):
    from atomicguard.application.agent import DualStateAgent  # Only when needed
    ...
```

**Benefit:** Core types and logic testable without atomicguard dependency.

## Directory Structure

```
infra_discovery/
├── agents/
│   ├── core/
│   │   ├── domain.py          (NodeId, Facet, Edge)
│   │   ├── belief_state.py    (BeliefState with RECORD, edges_to/from)
│   │   ├── agent_loop.py      (InfraDiscoveryAgent: flat loop, RELEVANT, INVOKE)
│   │   └── __init__.py
│   ├── scenarios/
│   │   ├── simple_topology.py (fixture scenario builder)
│   │   └── __init__.py
│   ├── fixtures/
│   │   └── simple_topology/
│   │       ├── github_actions-job-deploy.json
│   │       ├── kubernetes-Deployment-web.json
│   │       └── gcp-CloudRun_service-api.json
│   └── __init__.py
├── tests/
│   ├── test_agent_loop.py         (unit: NodeId, facets, bidirectional edges)
│   ├── test_bidirectional_discovery.py  (property-based: hypothesis)
│   ├── test_integration.py        (end-to-end with mocked atomicguard)
│   └── __init__.py
└── __init__.py
```

## What Works ✅

- [x] Compound `NodeId` equality, hashing, DSA-CATALOGUE dispatch
- [x] Facet accumulation (multiple independent observations per node)
- [x] Bidirectional edge discovery (`edges_from()` AND `edges_to()`)
- [x] Flat pending pool loop (no stack, phases, or position)
- [x] `RELEVANT()` de-duplication and scope checking
- [x] `INVOKE()` with fresh agent per call
- [x] `RECORD` / `RECORD-EDGE` into `belief_state`
- [x] End-to-end scenario execution
- [x] Type safety with proper ActionPair typing
- [x] Zero atomicguard runtime dependency (lazy import)

## What's Explicitly Deferred (Per Design)

**These do NOT belong in Step 1:**

- [ ] `requires` / `SWEEP-CLEARED` (AND-joins) → Step 2
- [ ] Acting DSAs (only sensing) → Step 5
- [ ] `IN-SCOPE` / budget bounding → Step 3
- [ ] `RECORD-UNCATALOGUED` → Step 4
- [ ] Real stochastic behavior (fixtures are deterministic) → later
- [ ] Property-based tests over cyclic graphs → Step 2

## Known Open Questions (Not Blocking)

Per open_questions.md:

- **OQ-002:** `belief_state` persistence backend (mutable vs. projection)
- **OQ-003:** Edge de-duplication / staleness handling
- **OQ-010:** Acting DSA selection strategy
- **OQ-017:** Reachability risk (requires targets not auto-enqueued) — validated as hand-designed constraint
- **OQ-018:** Whether sensing needs gating (currently ungated)

## Running the Tests

### Manual unit tests (no dependencies)
```bash
cd intelligent_agents
python3 -c "from infra_discovery.agents.core.domain import NodeId; ..."
```

### Integration test (with mocked atomicguard)
```bash
PYTHONPATH=. python3 infra_discovery/tests/test_integration.py
```

Expected output: ✅ PASS, 3 nodes, 4 edges, F-001 fix validated

### Property-based tests (requires hypothesis)
```bash
pip install hypothesis
pytest infra_discovery/tests/test_bidirectional_discovery.py -v
```

## Next Steps (Step 2)

Per step5_agent_program.md:

1. Add `requires` field to nodes (static catalogue-declared, not sensed)
2. Implement `SWEEP-CLEARED` iterative fixed-point pass
3. Add property-based tests for cyclic dependency graphs
4. Validate AND-join readiness mechanism with fixture topology

## Summary

**Step 1 complete.** The flat pending-pool agent loop works correctly with:
- ✅ Compound NodeId dispatch
- ✅ Facet accumulation
- ✅ Bidirectional edge discovery (F-001 validated)
- ✅ Type-safe implementation with lazy atomicguard import
- ✅ Full end-to-end scenario execution

Ready for Step 2: `requires` and `SWEEP-CLEARED`.
