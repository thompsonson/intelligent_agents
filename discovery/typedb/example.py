"""Walk the IA 13 pipeline with the belief state held in TypeDB.

    python -m discovery.typedb.example [--gated]

Needs a TypeDB 3.x server on 127.0.0.1:1729 (`make typedb-start`).
"""

import argparse
import json

from discovery.agents.discovery_agent import DiscoveryAgent
from discovery.core.environment import DiscoveryEnvironment
from discovery.scenarios.pipeline_fanout_lite import (
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
)
from discovery.typedb.belief_store import TypeDBBeliefStore, connect


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--gated",
        action="store_true",
        help="merge-gate requires lint and integration-tests (the AND-join)",
    )
    parser.add_argument("--database", default="ia13-discovery")
    args = parser.parse_args()

    nodes = (
        build_pipeline_fanout_lite_gated()
        if args.gated
        else build_pipeline_fanout_lite()
    )
    driver = connect()
    try:
        beliefs = TypeDBBeliefStore.fresh(driver, args.database, domain="pipeline")
        result = DiscoveryAgent(
            DiscoveryEnvironment(nodes), start_id="commit", beliefs=beliefs
        ).walk()

        print("Walk:", " -> ".join(result.path))
        print(f"Senses: {result.nodes_sensed}, moves: {result.total_cost}")
        print()
        print("Belief state, read back from TypeDB:")
        print(json.dumps(beliefs.belief_state(), indent=2))
        print()
        print("Derived, computed by TypeDB functions:")
        print("  reachable(commit):", sorted(beliefs.reachable("commit")))
        print("  is-leaf:", sorted(beliefs.leaves()))
        print()
        print(f"Database {args.database!r} is left in place to explore.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
