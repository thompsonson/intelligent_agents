"""DiscoveryAgent with its belief state in TypeDB.

Skipped unless the `typedb-driver` package is installed and a TypeDB 3.x
server answers on TYPEDB_ADDRESS (default 127.0.0.1:1729). Start one with
`make typedb-start`.
"""

import uuid

import pytest

typedb_driver = pytest.importorskip("typedb.driver")

from discovery.agents.discovery_agent import DiscoveryAgent  # noqa: E402
from discovery.core.environment import DiscoveryEnvironment  # noqa: E402
from discovery.scenarios.pipeline_fanout_lite import (  # noqa: E402
    build_pipeline_fanout_lite,
    build_pipeline_fanout_lite_gated,
    build_pipeline_fanout_lite_with_orphan_requirement,
)
from discovery.typedb.belief_store import TypeDBBeliefStore, connect  # noqa: E402

SCENARIOS = {
    "fanout-lite": build_pipeline_fanout_lite,
    "gated": build_pipeline_fanout_lite_gated,
    "orphan-requirement": build_pipeline_fanout_lite_with_orphan_requirement,
}


@pytest.fixture(scope="module")
def driver():
    try:
        drv = connect()
        drv.databases.all()
    except Exception as exc:  # no server: skip, don't fail
        pytest.skip(f"no TypeDB server: {exc}")
    yield drv
    drv.close()


@pytest.fixture
def store(driver):
    name = f"test-discovery-{uuid.uuid4().hex[:8]}"
    beliefs = TypeDBBeliefStore.fresh(driver, name, domain="pipeline")
    yield beliefs
    driver.databases.get(name).delete()


def _walk(nodes, beliefs=None):
    return DiscoveryAgent(
        DiscoveryEnvironment(nodes), start_id="commit", beliefs=beliefs
    ).walk()


class TestSameWalkEitherStore:
    @pytest.mark.parametrize("scenario", sorted(SCENARIOS))
    def test_typedb_walk_matches_in_memory(self, store, scenario):
        build = SCENARIOS[scenario]
        assert _walk(build(), store) == _walk(build())


class TestBeliefState:
    def test_held_beliefs_after_a_full_walk(self, store):
        _walk(build_pipeline_fanout_lite(), store)
        everything = {
            "commit",
            "lint",
            "unit-tests",
            "integration-tests",
            "merge-gate",
            "deploy",
        }
        assert store.known() == everything
        assert store.visited() == everything
        assert store.cleared() == everything
        assert store.blocked() == set()

    def test_orphan_requirement_is_known_but_never_visited(self, store):
        _walk(build_pipeline_fanout_lite_with_orphan_requirement(), store)
        assert "release-notes" in store.known()
        assert "release-notes" not in store.visited()
        assert store.blocked() == {"merge-gate"}


class TestDerived:
    def test_reachable_is_computed_over_sensed_edges(self, store):
        _walk(build_pipeline_fanout_lite(), store)
        assert store.reachable("commit") == {
            "lint",
            "unit-tests",
            "integration-tests",
            "merge-gate",
            "deploy",
        }
        assert store.reachable("deploy") == set()

    def test_is_leaf_is_deploy(self, store):
        _walk(build_pipeline_fanout_lite(), store)
        assert store.leaves() == {"deploy"}


class TestSchemaRefuses:
    """The schema enforces each predicate's Kind."""

    def _refused(self, store, query):
        with pytest.raises(typedb_driver.TypeDBDriverException):
            store._write([query])

    def test_notifies_recorded_as_controllable(self, store):
        store.record_sensed("commit", ("lint",), ())
        self._refused(
            store,
            'match $a isa node, has node-id "commit"; '
            '$b isa node, has node-id "lint"; '
            "insert $e isa notifies, links (source: $a, target: $b), "
            'has fact-kind "controllable", has sensed-at 2026-08-13T12:00:00, '
            'has sensed-by "agent";',
        )

    def test_visited_recorded_as_exogenous(self, store):
        store.record_known(["commit"])
        self._refused(
            store,
            'match $n isa node, has node-id "commit"; '
            "insert $v isa visited, links (subject: $n), "
            'has fact-kind "exogenous", has recorded-at 2026-08-13T12:00:00;',
        )

    def test_a_kind_outside_the_four(self, store):
        self._refused(
            store,
            'insert $n isa node, has node-id "x", has fact-kind "guessed";',
        )

    def test_notifies_without_its_kind(self, store):
        store.record_sensed("commit", ("lint",), ())
        self._refused(
            store,
            'match $a isa node, has node-id "commit"; '
            '$b isa node, has node-id "lint"; '
            "insert $e isa notifies, links (source: $a, target: $b), "
            'has sensed-at 2026-08-13T12:00:00, has sensed-by "agent";',
        )
