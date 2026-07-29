import pytest
from atomicguard.domain.models import AmbientEnvironment, Context
from atomicguard.infrastructure.guards.container_subprocess_guard import (
    ContainerSubprocessGuard,
)
from atomicguard.infrastructure.gym.precommit_generators import (
    LLMContainerFixGenerator,
)
from atomicguard.infrastructure.persistence.memory import InMemoryArtifactDAG

from real_task_graph_solver.atomicguard_backed.core.environment import (
    AtomicGuardCheckEnvironment,
)
from real_task_graph_solver.atomicguard_backed.core.llm_config import (
    DEFAULT_MODEL,
    OPENROUTER_PROVIDER,
    OR_KEY_ENV_VAR,
)
from real_task_graph_solver.atomicguard_backed.scenarios.type_check_repair import (
    BROKEN_STATES,
    FIXTURES_DIR,
    build_type_check_repair,
)


class TestBuildTypeCheckRepairWiring:
    def test_check_action_pair_runs_real_mypy_against_workdir(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes, goal = build_type_check_repair(workdir, api_key="dummy-key")

        node = nodes["type-check"]
        assert goal == "type-check"
        assert node.id == "type-check"
        generator = node.check_action_pair.generator
        assert generator._command == ["mypy", "src/"]
        assert generator._cwd == str(workdir)

    def test_repair_action_pair_uses_llm_container_fix_generator(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes, _goal = build_type_check_repair(
            workdir, model="some/model", api_key="dummy-key"
        )

        generator = nodes["type-check"].repair_action_pair.generator
        assert isinstance(generator, LLMContainerFixGenerator)
        assert generator._model == "some/model"
        assert generator._provider == OPENROUTER_PROVIDER
        assert generator._api_key == "dummy-key"
        assert generator._container_id is None
        assert generator._target_path == str(
            workdir / "src" / "example_pkg" / "domain.py"
        )

    def test_repair_action_pair_uses_default_model_when_not_given(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes, _goal = build_type_check_repair(workdir, api_key="dummy-key")

        assert nodes["type-check"].repair_action_pair.generator._model == DEFAULT_MODEL

    def test_repair_action_pair_guard_reruns_mypy_in_workdir(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes, _goal = build_type_check_repair(workdir, api_key="dummy-key")

        guard = nodes["type-check"].repair_action_pair.guard
        assert isinstance(guard, ContainerSubprocessGuard)
        assert guard._container_id is None
        assert str(workdir) in " ".join(guard._command)

    def test_broken_states_maps_type_check_to_typing_broken(self):
        assert BROKEN_STATES == {"type-check": "typing_broken"}

    def test_fixtures_dir_is_the_shared_example_pkg(self):
        assert FIXTURES_DIR.name == "example_pkg"


class TestOpenRouterApiKeyResolution:
    def test_raises_clearly_when_or_key_unset_and_no_api_key_given(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv(OR_KEY_ENV_VAR, raising=False)
        with pytest.raises(RuntimeError, match=OR_KEY_ENV_VAR):
            build_type_check_repair(tmp_path / "workdir")

    def test_uses_or_key_env_var_when_api_key_not_given(self, tmp_path, monkeypatch):
        monkeypatch.setenv(OR_KEY_ENV_VAR, "env-key")
        nodes, _goal = build_type_check_repair(tmp_path / "workdir")
        assert nodes["type-check"].repair_action_pair.generator._api_key == "env-key"


class TestRealMypyCheckWithoutNetwork:
    """The free-sensor half of this node needs no LLM at all - real mypy,
    real fixtures, no OpenRouter call. Only the repair half (an actual
    LLM fix) is untestable in this sandbox - see environment_design.md's
    note on why (openrouter.ai is blocked at the network-policy level
    here)."""

    def make_env(self, tmp_path):
        workdir = tmp_path / "workdir"
        nodes, goal = build_type_check_repair(workdir, api_key="dummy-key")
        return AtomicGuardCheckEnvironment(
            nodes,
            fixtures_dir=FIXTURES_DIR,
            workdir=workdir,
            goal=goal,
            broken_states=BROKEN_STATES,
        )

    def test_check_invariant_passes_on_clean(self, tmp_path):
        env = self.make_env(tmp_path)
        env.reset_to_state("clean")
        assert env.check_invariant("type-check") is True

    def test_check_invariant_fails_on_typing_broken_with_real_mypy_feedback(
        self, tmp_path
    ):
        env = self.make_env(tmp_path)
        env.reset_to_state("typing_broken")
        assert env.check_invariant("type-check") is False

        rejected = [
            a
            for a in env._dag.get_all_for_action_pair(
                action_pair_id="type-check", workflow_id=env._workflow_id
            )
            if a.status.value == "rejected"
        ]
        assert len(rejected) == 1
        assert "Incompatible return value type" in rejected[0].guard_result.feedback


class TestRepairPromptRendersWithRealFeedback:
    """A real bug found by a dry run against a dummy key, before any
    network call was ever attempted: PromptTemplate.render() raises
    ValueError if feedback_history is non-empty and feedback_wrapper is
    unset. Since check_action_pair and repair_action_pair share one
    action_pair_id, the repair's very first DualStateAgent call already
    has non-empty feedback_history (the check's real rejection, inherited
    through the shared DAG) - so this isn't an edge case, it's the normal
    path, and would have broken every real repair attempt regardless of
    network access or model choice."""

    def test_repair_prompt_template_renders_with_feedback_history_present(
        self, tmp_path
    ):
        workdir = tmp_path / "workdir"
        nodes, _goal = build_type_check_repair(workdir, api_key="dummy-key")
        prompt_template = nodes["type-check"].repair_action_pair._prompt_template

        context = Context(
            ambient=AmbientEnvironment(repository=InMemoryArtifactDAG()),
            specification="",
            feedback_history=(("previous file content", "mypy: real error text"),),
        )

        rendered = prompt_template.render(context)

        assert "mypy: real error text" in rendered
