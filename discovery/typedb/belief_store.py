"""A BeliefStore backed by TypeDB.

The schema (schema.tql beside this file) is the world ontology from IA
Series 13. Every fact the agent records carries its Kind, and TypeDB
refuses a fact whose Kind does not match its predicate. The derived facts -
reachable, is-leaf, blocked - are TypeDB functions: computed when asked,
never stored.

Needs a running TypeDB 3.x server and the `typedb-driver` package. See
documentation/discovery/typedb-belief-store/README.md.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from typedb.driver import (
    Credentials,
    Driver,
    DriverOptions,
    DriverTlsConfig,
    TransactionType,
    TypeDB,
)

SCHEMA_PATH = Path(__file__).with_name("schema.tql")


def connect(
    address: str = "",
    username: str = "",
    password: str = "",
) -> Driver:
    """Connect to a local TypeDB server without TLS.

    Defaults come from TYPEDB_ADDRESS, TYPEDB_USERNAME and TYPEDB_PASSWORD,
    then TypeDB's own defaults for a fresh local server.
    """
    return TypeDB.driver(
        address or os.environ.get("TYPEDB_ADDRESS", "127.0.0.1:1729"),
        Credentials(
            username or os.environ.get("TYPEDB_USERNAME", "admin"),
            password or os.environ.get("TYPEDB_PASSWORD", "password"),
        ),
        DriverOptions(DriverTlsConfig.disabled()),
    )


def _q(value: str) -> str:
    """A TypeQL string literal."""
    return json.dumps(value)


def _now() -> str:
    """A TypeQL datetime literal for now, in UTC."""
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="milliseconds")
    )


class TypeDBBeliefStore:
    """The agent's belief state, held in a TypeDB database.

    Use TypeDBBeliefStore.fresh() to start a walk from an empty belief
    state: it drops any database of that name and loads the schema.
    """

    def __init__(self, driver: Driver, database: str, sensed_by: str = "agent"):
        self._driver = driver
        self._database = database
        self._sensed_by = sensed_by

    @classmethod
    def fresh(
        cls,
        driver: Driver,
        database: str,
        domain: str = "",
        sensed_by: str = "agent",
    ) -> "TypeDBBeliefStore":
        if driver.databases.contains(database):
            driver.databases.get(database).delete()
        driver.databases.create(database)
        store = cls(driver, database, sensed_by)
        store._schema(SCHEMA_PATH.read_text())
        if domain:
            store._write(
                [
                    f"insert $d isa domain, has domain-name {_q(domain)}, "
                    f'has fact-kind "static";'
                ]
            )
        return store

    @property
    def database(self) -> str:
        return self._database

    # ---- transactions ----------------------------------------------------

    def _schema(self, query: str) -> None:
        with self._driver.transaction(self._database, TransactionType.SCHEMA) as tx:
            tx.query(query).resolve()
            tx.commit()

    def _write(self, queries: List[str]) -> None:
        """Run the queries in one write transaction: all commit, or none."""
        with self._driver.transaction(self._database, TransactionType.WRITE) as tx:
            for query in queries:
                tx.query(query).resolve()
            tx.commit()

    def _fetch(self, query: str) -> List[Dict]:
        with self._driver.transaction(self._database, TransactionType.READ) as tx:
            return list(tx.query(query).resolve().as_concept_documents())

    def _ids(self, query: str) -> Set[str]:
        return {doc["id"] for doc in self._fetch(query)}

    def _put_node(self, node_id: str) -> str:
        return f'put $n isa node, has node-id {_q(node_id)}, has fact-kind "exogenous";'

    # ---- exogenous: sensed facts -----------------------------------------

    def has_sensed(self, node_id: str) -> bool:
        return bool(
            self._fetch(
                f"match $n isa node, has node-id {_q(node_id)}, has sensed-at $t; "
                f'fetch {{ "id": $n.node-id }};'
            )
        )

    def record_sensed(
        self, node_id: str, notifies: Tuple[str, ...], requires: Tuple[str, ...]
    ) -> None:
        """Record one sensing of node_id. Called once per node: the schema
        allows one sensed-at per node, so a second call is refused.
        Re-sensing is not part of IA 13's loop."""
        at, by = _now(), _q(self._sensed_by)
        queries = [self._put_node(node_id)]
        queries.append(
            f"match $n isa node, has node-id {_q(node_id)}; "
            f"insert $n has sensed-at {at}, has sensed-by {by};"
        )
        for relation, here, there, targets in (
            ("notifies", "source", "target", notifies),
            ("requires", "dependent", "dependency", requires),
        ):
            for target in targets:
                queries.append(self._put_node(target))
                queries.append(
                    f"match $a isa node, has node-id {_q(node_id)}; "
                    f"$b isa node, has node-id {_q(target)}; "
                    f"insert $e isa {relation}, links ({here}: $a, {there}: $b), "
                    f'has fact-kind "exogenous", has sensed-at {at}, '
                    f"has sensed-by {by};"
                )
        self._write(queries)

    def _targets(self, relation: str, here: str, there: str, node_id: str):
        return tuple(
            sorted(
                self._ids(
                    f"match $a isa node, has node-id {_q(node_id)}; "
                    f"$e isa {relation}, links ({here}: $a, {there}: $b); "
                    f'fetch {{ "id": $b.node-id }};'
                )
            )
        )

    def notifies_of(self, node_id: str) -> Tuple[str, ...]:
        return self._targets("notifies", "source", "target", node_id)

    def requires_of(self, node_id: str) -> Tuple[str, ...]:
        return self._targets("requires", "dependent", "dependency", node_id)

    def sensed_edges(self) -> List[Tuple[str, str]]:
        docs = self._fetch(
            "match $e isa notifies, links (source: $a, target: $b); "
            'fetch { "from": $a.node-id, "to": $b.node-id };'
        )
        return sorted((doc["from"], doc["to"]) for doc in docs)

    # ---- controllable: the agent's own beliefs ---------------------------

    def _record(self, relation: str, node_id: str) -> List[str]:
        """Record relation(node_id) once: a second record is a no-op."""
        return [
            self._put_node(node_id),
            f"match $n isa node, has node-id {_q(node_id)}; "
            f"not {{ $r isa {relation}, links (subject: $n); }}; "
            f"insert $r isa {relation}, links (subject: $n), "
            f'has fact-kind "controllable", has recorded-at {_now()};',
        ]

    def record_known(self, node_ids: Iterable[str]) -> None:
        queries: List[str] = []
        for node_id in dict.fromkeys(node_ids):
            queries.extend(self._record("known", node_id))
        self._write(queries)

    def record_visited(self, node_id: str) -> None:
        self._write(self._record("visited", node_id))

    def record_cleared(self, node_id: str) -> None:
        self._write(self._record("cleared", node_id))

    def _held(self, relation: str) -> Set[str]:
        return self._ids(
            f"match $r isa {relation}, links (subject: $n); "
            f'fetch {{ "id": $n.node-id }};'
        )

    def known(self) -> Set[str]:
        return self._held("known")

    def visited(self) -> Set[str]:
        return self._held("visited")

    def cleared(self) -> Set[str]:
        return self._held("cleared")

    # ---- derived: TypeDB functions, computed when asked ------------------

    def reachable(self, node_id: str) -> Set[str]:
        return self._ids(
            f"match $a isa node, has node-id {_q(node_id)}; "
            f"let $b in reachable($a); "
            f'fetch {{ "id": $b.node-id }};'
        )

    def leaves(self) -> Set[str]:
        return self._ids('match let $n in is-leaf(); fetch { "id": $n.node-id };')

    def blocked(self) -> Set[str]:
        return self._ids('match let $n in blocked(); fetch { "id": $n.node-id };')

    def belief_state(self) -> Dict[str, List[str]]:
        """The belief state in IA 13's shape: known, visited, cleared (held)
        and blocked (derived)."""
        return {
            "known": sorted(self.known()),
            "visited": sorted(self.visited()),
            "cleared": sorted(self.cleared()),
            "blocked": sorted(self.blocked()),
        }
