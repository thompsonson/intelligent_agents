# Step 1 Topology Visualizations

## Simple Topology (3 Nodes, 4 Edges)

### Discovery Flow

```
STEP 1: Sense root
┌─────────────────────────────────────────────────────────────┐
│ github_actions/job/deploy                                   │
│   sensed_by: DSA-GH-JOB-WATCH                              │
│   facets: {conclusion: success, status: completed}          │
│   discovers edges to:                                       │
│     → kubernetes/Deployment/web   (applies-to)              │
│     → gcp/CloudRun_service/api    (applies-to)              │
└─────────────────────────────────────────────────────────────┘
                            ↓↓
pending = { (DSA-K8S-DEPLOYMENT-GET, kubernetes/Deployment/web),
            (DSA-GCP-RUN-SERVICE, gcp/CloudRun_service/api) }

STEP 2: Sense kubernetes/Deployment/web
┌─────────────────────────────────────────────────────────────┐
│ kubernetes/Deployment/web                                   │
│   sensed_by: DSA-K8S-DEPLOYMENT-GET                        │
│   facets: {replicas: 3, ready_replicas: 3, status: Active}│
│   discovers edges to:                                       │
│     → github_actions/job/deploy (deployed-by, reverse)     │
└─────────────────────────────────────────────────────────────┘
                            ↓↓
STEP 3: Sense gcp/CloudRun_service/api
┌─────────────────────────────────────────────────────────────┐
│ gcp/CloudRun_service/api                                    │
│   sensed_by: DSA-GCP-RUN-SERVICE                           │
│   facets: {status: RUNNING, uri: https://...run.app}      │
│   discovers edges to:                                       │
│     → github_actions/job/deploy (deployed-by, reverse)     │
└─────────────────────────────────────────────────────────────┘
                            ↓↓
pending = ∅
STATUS: DONE
```

### Final Graph (All Bidirectional per F-001)

```
                    ┌──────────────────────┐
                    │   github_actions     │
                    │   job/deploy         │
                    │   2 facets           │
                    └──────┬────┬──────────┘
                           │    │
              applies-to   │    │  applies-to
                           │    │
                  ╔════════╩╗  ╔╩════════╗
                  ║ F-001   ║  ║ F-001   ║
                  ║ reverse ║  ║ reverse ║
                  ╚════════╦╝  ╚╦════════╝
                           │    │
                    ┌──────▼─┐  └──────┐
                    │ kubernetes       │ gcp
                    │ Deployment/web   │ CloudRun_service/api
                    │ 3 facets         │ 3 facets
                    └──────────────────┘
```

**Edges (queryable both directions):**
- `deploy --applies-to--> web` ✓ (forward + reverse)
- `deploy --applies-to--> api` ✓ (forward + reverse)
- `web --deployed-by--> deploy` ✓ (backward edge)
- `api --deployed-by--> deploy` ✓ (backward edge)

---

## Fan-Out Topology (1 Root → 5 Leaves)

### Discovery Pattern

```
Step 1: Root discovers 5 targets in ONE shot
┌──────────────────────────────────────────────────────────────┐
│  github_actions/job/deploy                                   │
│  (artifact contains 5 edges)                                 │
└──────────────────────────┬─────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┬──────────────────┐
        │                  │                  │                  │
    applies-to         applies-to         applies-to         applies-to
        │                  │                  │                  │
        ▼                  ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ K8s      │      │ K8s      │      │ GCP      │      │ GCP      │
    │ Service/ │      │ Service/ │      │ CloudRun │      │ CloudRun │
    │ web      │      │ api      │      │ gateway  │      │ worker   │
    │ 3 facets │      │ 3 facets │      │ 2 facets │      │ 2 facets │
    └──────────┘      └──────────┘      └──────────┘      └──────────┘
    
    ╔═══════════════════════════════════════════════════════════════╗
    ║ ALSO discovers:  aws/EC2_instance/cache (unregistered)        ║
    ║ Status: Discovered but not sensed (OQ-015)                   ║
    ╚═══════════════════════════════════════════════════════════════╝

Steps 2-6: Sense each discovered node
    Each node: RELEVANT → de-dup → INVOKE → RECORD facets
    No new edges discovered from leaves (fan-out, not deeper)
    pending pool: 5 → 4 → 3 → 2 → 1 → 0
    STATUS: DONE (all leaves have no further edges)
```

### Pending Pool Evolution

```
Initial:     pending = {
               (DSA-K8S-SERVICE, kubernetes/Service/web),
               (DSA-K8S-SERVICE, kubernetes/Service/api),
               (DSA-GCP-RUN, gcp/CloudRun_service/gateway),
               (DSA-GCP-RUN, gcp/CloudRun_service/worker),
               (no DSA for aws/EC2) ← OQ-015: dead-end
             }

After step 2: pending = {web, api, gateway, worker}  (minus 1)
After step 3: pending = {api, gateway, worker}       (minus 1)
After step 4: pending = {gateway, worker}            (minus 1)
After step 5: pending = {worker}                     (minus 1)
After step 6: pending = {}                           → DONE
```

---

## Chain Topology (4 Hops, F-001 Reverse Edges)

### Discovery Trace

```
STEP 1: Root → Deployment
┌─────────────────────────────────────┐
│ github_actions/job/deploy           │
│   → kubernetes/Deployment/api       │
└─────────────────────────────────────┘
          ↓↓
pending = {(DSA-K8S-DEPLOYMENT-GET, kubernetes/Deployment/api)}

STEP 2: Deployment → Backend + Root
┌─────────────────────────────────────┐
│ kubernetes/Deployment/api           │
│   → gcp/CloudRun_service/backend    │
│   → github_actions/job/deploy (F-001 reverse)
└─────────────────────────────────────┘
          ↓↓
pending = {(DSA-GCP-RUN, gcp/CloudRun_service/backend)}
          ← root already sensed, de-dup by RELEVANT

STEP 3: Backend → Database + Deployment
┌─────────────────────────────────────┐
│ gcp/CloudRun_service/backend        │
│   → external/database/postgres (no DSA)
│   → kubernetes/Deployment/api (F-001 reverse)
└─────────────────────────────────────┘
          ↓↓
pending = {}  (postgres: no DSA; deployment: already recorded)
STATUS: DONE (3 nodes discovered, 1 dead-end)
```

### Graph Structure

```
     Hop 1      Hop 2         Hop 3          Hop 4
  ┌──────┐    ┌──────┐      ┌────────┐    ┌──────────┐
  │ GH   │───→│ K8s  │─────→│  GCP   │───→│ External │
  │ job  │    │Deploy│      │ Backend│    │ Database │
  │Deploy│    │  api │      │        │    │(dead-end)│
  └──────┘    └──────┘      └────────┘    └──────────┘
    ▲           ▲ ▲           ▲ ▲
    │           │ │           │ │
    │ F-001     │ │ F-001     │ │ (no F-001:
    │ reverse   │ │ reverse   │ │  no reverse edge
    │           └─┘           └─┘  from external)
    │___________________________|
           (all edges loop back via F-001 reverse)
```

**5 Total Edges:**
1. `deploy → api` (applies-to, forward)
2. `api → backend` (enables, forward)
3. `backend → postgres` (depends-on-external, forward; dead-end)
4. `api ← deploy` (deployed-by, F-001 reverse)
5. `backend ← api` (enabled-by, F-001 reverse)

**All bidirectional-queryable except postgres (no DSA to return reverse).**

---

## Key Insights from Visualizations

### 1. **Pending Pool Scaling**
- **Width** (fan-out): pool grows linearly with targets; no quadratic blowup
- **Depth** (chain): pool shrinks after each node; no stack needed
- **Cycles** (F-001 reverses): already-sensed nodes de-dup'd by RELEVANT

### 2. **F-001 Reverse Edges (Bidirectional Discovery)**
- Root discovers leaves in ONE sensed artifact
- Leaves later discover root VIA reverse edges in THEIR artifacts
- Both directions queryable via `edges_from()` and `edges_to()`
- **Critical:** without F-001, chain topology stops at deployment; never reaches backend

### 3. **Dead-Ends (OQ-015)**
- Unregistered kinds (`aws/EC2`) are discovered but never sensed
- Edge still exists; just no DSA to invoke
- **Step 4** will add `RECORD-UNCATALOGUED` to track these visibly

### 4. **Facet Accumulation**
- Each node can be sensed by multiple DSAs
- Facets accumulate per node (not per DSA)
- Example: `kubernetes/Deployment` has `{replicas, ready_replicas, status}` from multiple sources
- No overwrites; independent observations coexist

---

## How to Generate Animated Visualizations

For GIF animations (like `real_discovery/atomicguard_backed/animations/`):

```bash
# 1. Create a visualization script
python3 -c "
import infra_discovery.agents.scenarios.simple_topology as s
agent = s.build_simple_topology_agent()
# Hook into step() to capture state after each turn
# Use matplotlib/graphviz to render frames
# ffmpeg to stitch into GIF
"

# 2. Render using Graphviz
dot -Tgif -o simple_topology.gif diagram.dot

# 3. Animate with ffmpeg
ffmpeg -i frame_%03d.png -vf "fps=2" simple_topology.gif
```

**Status:** Not yet implemented. Requires:
- Frame capture hook in agent loop
- Graphviz/dot layout engine
- ffmpeg for animation

Would be valuable for:
- Blog posts / documentation
- Conference talks
- Understanding discovery patterns visually

---

## Summary Table

| Topology | Nodes | Edges | Hops | Width | Bidirectional | Dead-Ends |
|----------|-------|-------|------|-------|---------------|-----------|
| Simple | 3 | 4 | 1 | 2 | 4/4 (100%) | 0 |
| Fan-Out | 5 | 5 | 1 | 5 | 5/5 (100%) | 1 (aws/EC2) |
| Chain | 3 | 5 | 3 | 1 | 4/5 (80%*) | 1 (postgres) |

*postgres has no reverse because external/database has no DSA
