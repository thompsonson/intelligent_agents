import json

import pytest
from atomicguard.application.action_pair import ActionPair
from atomicguard.contrib.guards.exit_code_guard import ExitCodeGuard
from atomicguard.domain.prompts import PromptTemplate
from atomicguard.infrastructure.generators.subprocess_generator import (
    SubprocessGenerator,
)

from real_discovery.atomicguard_backed.core.domain import StatefulDiscoveryNode
from real_discovery.atomicguard_backed.core.environment import (
    StatefulDiscoveryEnvironment,
)


def make_check_action_pair(tmp_path, node_id, notifies):
    """A real `cat` over a real fixture file - the same shape the
    pipeline_fanout_lite scenario itself uses, not a mock. See
    scenarios/pipeline_fanout_lite.py."""
    fixture = tmp_path / f"{node_id}.json"
    fixture.write_text(json.dumps({"notifies": list(notifies)}))
    return ActionPair(
        generator=SubprocessGenerator(command=["cat", str(fixture)]),
        guard=ExitCodeGuard(),
        prompt_template=PromptTemplate(role="", constraints="", task=""),
    )


def make_node(tmp_path, node_id, notifies=(), requires=()):
    return StatefulDiscoveryNode(
        id=node_id,
        check_action_pair=make_check_action_pair(tmp_path, node_id, notifies),
        requires=requires,
    )


class TestGraphValidation:
    def test_requires_referencing_unknown_node_is_rejected(self, tmp_path):
        nodes = {"a": make_node(tmp_path, "a", requires=("does-not-exist",))}
        with pytest.raises(ValueError, match="does-not-exist"):
            StatefulDiscoveryEnvironment(nodes)

    def test_cycle_is_rejected(self, tmp_path):
        nodes = {
            "a": make_node(tmp_path, "a", requires=("b",)),
            "b": make_node(tmp_path, "b", requires=("a",)),
        }
        with pytest.raises(ValueError, match="cycle"):
            StatefulDiscoveryEnvironment(nodes)


class TestSenseEdges:
    def test_reads_notifies_off_a_real_check_run(self, tmp_path):
        nodes = {
            "commit": make_node(tmp_path, "commit", notifies=("lint", "unit-tests")),
            "lint": make_node(tmp_path, "lint"),
            "unit-tests": make_node(tmp_path, "unit-tests"),
        }
        env = StatefulDiscoveryEnvironment(nodes)
        assert env.sense_edges("commit") == ("lint", "unit-tests")

    def test_no_notifies_returns_empty_tuple(self, tmp_path):
        nodes = {"deploy": make_node(tmp_path, "deploy")}
        env = StatefulDiscoveryEnvironment(nodes)
        assert env.sense_edges("deploy") == ()

    def test_unknown_node_id_raises(self, tmp_path):
        nodes = {"a": make_node(tmp_path, "a")}
        env = StatefulDiscoveryEnvironment(nodes)
        with pytest.raises(ValueError, match="not a node"):
            env.sense_edges("does-not-exist")

    def test_notifies_target_unknown_to_the_graph_raises_at_sense_time(self, tmp_path):
        # Can't be caught at construction: a node's notifies genuinely
        # isn't knowable until its check_action_pair actually runs. See
        # environment_design.md's "Sense-time, not construction-time".
        nodes = {"a": make_node(tmp_path, "a", notifies=("ghost",))}
        env = StatefulDiscoveryEnvironment(nodes)
        with pytest.raises(ValueError, match="ghost"):
            env.sense_edges("a")

    def test_each_sense_is_a_real_subprocess_call(self, tmp_path):
        # No caching in the environment itself - re-sensing re-runs the
        # real check. DiscoveryAgent is the one that avoids re-sensing an
        # already-known node; this environment doesn't need to.
        nodes = {"a": make_node(tmp_path, "a", notifies=("b",)), "b": make_node(tmp_path, "b")}
        env = StatefulDiscoveryEnvironment(nodes)
        env.sense_edges("a")
        assert env.sense_edges("a") == ("b",)
        artifacts = env._dag.get_all_for_action_pair(
            action_pair_id="a", workflow_id=env._workflow_id
        )
        assert len(artifacts) == 2


class TestSenseRequires:
    def test_returns_declared_requires(self, tmp_path):
        nodes = {
            "lint": make_node(tmp_path, "lint"),
            "integration-tests": make_node(tmp_path, "integration-tests"),
            "merge-gate": make_node(
                tmp_path, "merge-gate", requires=("lint", "integration-tests")
            ),
        }
        env = StatefulDiscoveryEnvironment(nodes)
        assert env.sense_requires("merge-gate") == ("lint", "integration-tests")
        assert env.sense_requires("lint") == ()

    def test_unknown_node_id_raises(self, tmp_path):
        nodes = {"a": make_node(tmp_path, "a")}
        env = StatefulDiscoveryEnvironment(nodes)
        with pytest.raises(ValueError, match="not a node"):
            env.sense_requires("does-not-exist")


class TestGetMoveCost:
    def test_always_one(self, tmp_path):
        nodes = {"a": make_node(tmp_path, "a"), "b": make_node(tmp_path, "b")}
        env = StatefulDiscoveryEnvironment(nodes)
        assert env.get_move_cost("a", "b") == 1
        assert env.get_move_cost("b", "a") == 1
