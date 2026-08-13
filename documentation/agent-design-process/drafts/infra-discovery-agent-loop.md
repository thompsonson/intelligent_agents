# Draft: The infra discovery agent — the agent loop

*Draft material for future work on modelling the infra discovery agent's loop. These two diagrams are the agent side (the **agent ontology**), not the world ontology — the world-ontology diagrams (vocab graph, instance topology, belief lifecycle, belief-building sequence) live in the [IA Series 13 post](../blog.md). Reviewed here before deciding where the agent-loop treatment goes.*

## The walk loop, as a flow

The discovery agent's decision loop: sense the node you're at, fold it into belief, and move on — forward while there are unvisited candidates, backtrack when there are none, and a readiness sweep re-opens blocked nodes once their requirements clear.

```mermaid
flowchart TD
    Start([at a node]) --> Sense["SENSE(node)"]
    Sense --> Merge["RECORD known / visited / cleared"]
    Merge --> Candidates{"unvisited notifies?"}
    Candidates -- yes --> Walk["WALK(min id)"] --> Start
    Candidates -- no --> Back{"parents remain?"}
    Back -- yes --> Backtrack["WALK(parent)"] --> Start
    Back -- no --> Sweep{"blocked nodes newly clear?"}
    Sweep -- yes --> Route["replay known route"] --> Start
    Sweep -- no --> Report["REPORT(descriptor)"] --> Done([done])

    classDef action fill:#3b4a5a,color:#fff,stroke:#222
    classDef state fill:#2f6690,color:#fff,stroke:#1c3d52
    class Sense,Walk,Backtrack,Route,Report action
    class Start,Merge,Done state
```

## The implementation, as a class diagram

The program surface of `discovery/` — the environment withholds the graph and answers only sense queries; the agent owns position and belief; the result reports the walk.

```mermaid
classDiagram
    class DiscoveryNode {
        +str id
        +Tuple notifies
        +Tuple requires
    }

    class DiscoveryEnvironment {
        +Dict nodes
        +sense_edges(node_id) Tuple
        +sense_requires(node_id) Tuple
        +get_move_cost(from, to) int
    }

    class DiscoveryAgent {
        -DiscoveryEnvironment environment
        -str start_id
        +walk() DiscoveryWalkResult
    }

    class DiscoveryWalkResult {
        +List path
        +int nodes_sensed
        +bool goal_reached
        +int total_cost
        +List blocked_nodes
    }

    DiscoveryAgent --> DiscoveryEnvironment
    DiscoveryAgent --> DiscoveryWalkResult
    DiscoveryEnvironment --> DiscoveryNode
```
