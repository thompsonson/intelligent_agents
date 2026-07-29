import pytest

from real_task_graph_solver.core.domain import RealCheckNode


class TestRealCheckNode:
    def test_holds_id_command_and_requires(self):
        node = RealCheckNode(id="type-check", command=("mypy", "src/"))

        assert node.id == "type-check"
        assert node.command == ("mypy", "src/")
        assert node.requires == ()

    def test_requires_defaults_to_empty_tuple(self):
        node = RealCheckNode(id="a", command=("true",))
        assert node.requires == ()

    def test_requires_can_be_set(self):
        node = RealCheckNode(id="release-ready", command=("true",), requires=("a", "b"))
        assert node.requires == ("a", "b")

    def test_has_no_pass_probability_rmax_or_retry_flavor(self):
        # Deliberately smaller than TaskNode - see
        # documentation/task-graph/real-guards/environment_design.md.
        node = RealCheckNode(id="a", command=("true",))
        assert not hasattr(node, "pass_probability")
        assert not hasattr(node, "rmax")
        assert not hasattr(node, "r_patience")
        assert not hasattr(node, "retry_flavor")

    def test_empty_command_is_rejected(self):
        with pytest.raises(ValueError):
            RealCheckNode(id="a", command=())
