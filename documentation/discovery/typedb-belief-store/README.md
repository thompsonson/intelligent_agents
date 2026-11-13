# TypeDB as the discovery agent's belief store

A practical example for [IA Series 13: Ontologies, Doctrine, and Ubiquitous Language](../../ia-series/13-ontologies/blog.md).
The post's world ontology becomes a TypeDB schema, and `DiscoveryAgent` keeps its belief
state in TypeDB instead of in Python sets. The walk is unchanged.

## What it shows

- **The schema is the world ontology.** `discovery/typedb/schema.tql` writes the post's
  entities and predicates as TypeDB types: `node`, `notifies`, `requires`, `known`,
  `visited`, `cleared`, and a static `domain`.
- **Kind lives in the data, and the schema enforces it.** The post notes that RDF(S),
  OWL and schema.org cannot say whether a fact is exogenous, controllable, static or
  derived. Here every fact carries a `fact-kind`, and each predicate pins its own:
  - a `notifies` recorded as controllable is refused;
  - a `visited` recorded as exogenous is refused;
  - a Kind outside the four is refused;
  - a fact with no Kind is refused.
- **Derived facts are computed, never asserted.** `reachable`, `is-leaf` and `blocked`
  are TypeDB functions. They answer when asked and store nothing. `reachable` is
  recursive and stops on a cycle.
- **SENSE → RECORD.** The agent records each sensed node's `notifies` and `requires` as
  exogenous facts, with `sensed-at` and `sensed-by`. It then records its own `known`,
  `visited` and `cleared` as controllable facts.

## How the post's tables map

| IA 13 | Kind | TypeDB |
|---|---|---|
| `node(id)` | exogenous | entity `node`, key `node-id` |
| `notifies(id, target)` | exogenous | relation `notifies` (`source`, `target`) |
| `requires(id, target)` | exogenous | relation `requires` (`dependent`, `dependency`) |
| `known(id)`, `visited(id)`, `cleared(id)` | controllable | relations `known`, `visited`, `cleared`, each with one `subject` |
| `domain` | static | entity `domain` |
| `reachable(from, to)` | derived | function `reachable($from)` |
| `is-leaf(id)` | derived | function `is-leaf()` |
| `blocked` (Status) | derived here | function `blocked()`: visited and not cleared |

- **`fact-kind`, not `kind`.** In TypeQL, "kind" already means entity, relation or
  attribute.
- **`blocked`.** The post lists it as a Status and in the belief state's JSON. The agent
  has always derived it (visited minus cleared), so here it is a function.

## How the agent uses it

- `DiscoveryAgent` reads and writes its beliefs only through a `BeliefStore`
  (`discovery/core/belief_store.py`).
- The default, `InMemoryBeliefStore`, holds what the agent used to hold inside `walk()`.
  The existing tests pass unchanged.
- `TypeDBBeliefStore` (`discovery/typedb/belief_store.py`) holds the same beliefs in
  TypeDB. The tests check the walk is identical with either store, on all three
  `pipeline_fanout_lite` scenarios.

## Running it

```bash
make typedb-start                 # TypeDB 3.14.2 in Docker, on 127.0.0.1 only
uv pip install typedb-driver==3.14.0
make discovery-typedb-example     # the gated walk, then the belief state and derived facts
make test-discovery               # includes the TypeDB tests while the server is up
```

- The example leaves its database, `ia13-discovery`, in place to explore, for instance in
  TypeDB Studio.
- The connection defaults to `127.0.0.1:1729` and TypeDB's own defaults for a fresh local
  server. `TYPEDB_ADDRESS`, `TYPEDB_USERNAME` and `TYPEDB_PASSWORD` override them.
- Without a server, or without the driver, the TypeDB tests are skipped.

## Not covered

- **Re-sensing.** Each node is sensed once, and the schema allows one `sensed-at` per
  node. Re-sensing a node whose belief may have gone out of date is not part of IA 13's
  loop.
