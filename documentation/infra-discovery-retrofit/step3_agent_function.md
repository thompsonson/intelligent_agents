# Infra Discovery: Agent Function (Step 3)

**Status: Stub.** Same shape of gap as
[`step1_environment_specification.md`](step1_environment_specification.md) (Step 1):
checked directly, no file in the original `documentation/infra-discovery/`
owns this content. `step4_algorithm_fit.md` (Step 4) reasons extensively *about*
an agent function - fit arguments, soundness questions, literature grounding
- but the agent function itself, the actual percept→action mapping and its
pseudocode, is never stated for this track. It's referenced, at second hand,
from `atomicguard`.

## Where the real content currently lives

Entirely in `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md`
("Step 3: Agent Function" section, lines 335-621) and its revision,
`topology_agent_function_requires_and_discovery_validation.md` ("Revised
pseudocode" section). Both are cited by name throughout this track's other
documents (`step2_environment_analysis.md`, `step4_algorithm_fit.md`) but never
translated into this track's own words the way `step2_environment_analysis.md`
translated the Node/Edge ontology from the same source document.

## What translating this file for real would need to cover

Mirroring what `step2_environment_analysis.md`/`step0_schema.md` already did for the
ontology - restate in this track's own terms, checked against the source,
not just cited:

- **Percepts** - what a DSA invocation's `Artifact` looks like as a percept
  here, parallel to `step0_schema.md`'s `Facet` shape.
- **Actions** - the DSA vocabulary (`INVOKE(dsa, subject)`), and how
  `pending`/`SELECT-NEXT` structure the action space - `step4_algorithm_fit.md`
  already argues *why* this replaces `DiscoveryAgent.walk()`'s LIFO stack,
  but the actual function definition (percept sequence → action) isn't
  written out here.
- **The pseudocode itself** - `AGENT-FUNCTION`'s current, revised form
  (`RESOLVE-BRIDGES`, `RELEVANT`, `ELIGIBLE`, `SELECT-NEXT`/`SCORE`,
  `IN-SCOPE`), translated into this track's own worked trace the way
  `step4_algorithm_fit.md`'s Mermaid sequence diagrams did for
  `atomicguard-bridge/`'s smaller case.
- **Cost features** - named in the source document, never checked against
  this track's actual three domains (GitHub/K8s/gcloud) the way
  `step0_schema.md`'s `DSA-CATALOGUE` tables checked the ontology against them.

This is, alongside `step1_environment_specification.md`, the retrofit's other
real finding: two of five steps have no owned content for this track at
all, not a filing problem solvable by moving text between files.

## Related documents

- [`step4_algorithm_fit.md`](step4_algorithm_fit.md) - Step 4; reasons about this step's output without this file existing to reason from.
- `atomicguard`'s `docs/design/notes/topology_sensing_dsa_belief_state_and_agent_function.md` - Step 3's actual pseudocode, owned by `atomicguard`, not this track.
- `atomicguard`'s `docs/design/notes/topology_agent_function_requires_and_discovery_validation.md` - the revised pseudocode.
- `RETROFIT_SIZING.md` - this stub counted as net-new work in the overall sizing.
