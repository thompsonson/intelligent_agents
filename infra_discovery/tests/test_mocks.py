"""Test mocks matching real atomicguard interfaces.

These mocks implement the ACTUAL signatures and behavior of atomicguard classes,
not simplified versions. This catches integration bugs that only appear with
real atomicguard, as identified in PR #16 review issue #4.

Per real interfaces from atomicguard:
- ActionPairInterface: generator, guard, pre_guard (optional), effector (optional)
- DualStateAgent: requires artifact_dag (not optional)
- ArtifactDAGInterface: store/retrieve Artifacts
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MockContext:
    """Mock Context matching atomicguard.domain.models.Context."""

    artifacts: tuple = ()
    types: tuple = ()
    contexts: tuple = ()


@dataclass
class MockGenerator:
    """Mock generator that returns fixture content."""

    content: Dict[str, Any]

    def generate(self, context: Any = None) -> str:
        """Return stringified fixture content."""
        return str(self.content)


@dataclass
class MockGuard:
    """Mock guard that always passes (ExitCodeGuard behavior for cat)."""

    def validate(self, artifact: Any) -> bool:
        """Always pass - fixture content is valid."""
        return True


@dataclass
class MockActionPair:
    """Mock ActionPair matching real interface (without id attribute).
    
    Real ActionPair has:
    - generator: GeneratorInterface (property)
    - guard: GuardInterface (property)
    - pre_guard: Optional[GuardInterface] (property)
    - effector: Optional[EffectorInterface] (property)
    
    It DOES NOT have an .id attribute (fixes PR #16 issue #2).
    """

    _generator: MockGenerator
    _guard: MockGuard
    _pre_guard: Optional[MockGuard] = None
    _effector: Optional[Any] = None

    @property
    def generator(self) -> MockGenerator:
        """Access the generator (read-only)."""
        return self._generator

    @property
    def guard(self) -> MockGuard:
        """Access the post-guard (read-only)."""
        return self._guard

    @property
    def pre_guard(self) -> Optional[MockGuard]:
        """Access the pre-guard (read-only)."""
        return self._pre_guard

    @property
    def effector(self) -> Optional[Any]:
        """Access the effector (read-only)."""
        return self._effector


@dataclass
class MockArtifactDAG:
    """Mock ArtifactDAGInterface for testing.
    
    Real ArtifactDAGInterface stores and retrieves Artifacts.
    Fixes PR #16 issue #3 (artifact_dag was None, requiring real DAG).
    """

    artifacts: Dict[str, Any] = field(default_factory=dict)

    def store(self, artifact: Any) -> None:
        """Store an artifact."""
        artifact_id = getattr(artifact, "id", "default")
        self.artifacts[str(artifact_id)] = artifact

    def retrieve(self, artifact_id: str) -> Optional[Any]:
        """Retrieve an artifact."""
        return self.artifacts.get(artifact_id)

    def retrieve_by_workflow(self, workflow_id: str) -> list:
        """Retrieve all artifacts for a workflow."""
        return [
            a
            for a in self.artifacts.values()
            if getattr(a, "workflow_id", None) == workflow_id
        ]


@dataclass
class MockArtifact:
    """Mock Artifact matching atomicguard schema."""

    id: str
    workflow_id: str
    content: Dict[str, Any]
    status: str = "success"
    artifact_type: str = "fixture"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "content": self.content,
            "status": self.status,
            "artifact_type": self.artifact_type,
        }


class MockDualStateAgent:
    """Mock DualStateAgent matching real interface (fixes PR #16 issue #3).
    
    Real DualStateAgent.__init__ signature:
        def __init__(
            self,
            action_pair: ActionPairInterface,
            artifact_dag: ArtifactDAGInterface,  # REQUIRED, not optional
            rmax: int = 3,
            action_pair_id: str = "unknown",
            workflow_id: str = "unknown",
            ...
        )
    
    Real DualStateAgent.execute() returns an Artifact.
    """

    def __init__(
        self,
        action_pair: MockActionPair,
        artifact_dag: MockArtifactDAG,
        rmax: int = 3,
        action_pair_id: str = "unknown",
        workflow_id: str = "unknown",
        constraints: str = "",
        r_patience: Optional[int] = None,
        e_max: int = 1,
        escalate_feedback_to: Optional[list] = None,
        escalate_feedback_by_guard: Optional[Dict] = None,
        artifact_type: Optional[str] = None,
        dependency_artifact_contexts: Optional[Dict] = None,
        artifact_context: Optional[str] = None,
    ):
        """Initialize with required artifact_dag (fixes PR #16 issue #3).
        
        This matches the real interface - artifact_dag is NOT optional.
        """
        self.action_pair = action_pair
        self.artifact_dag = artifact_dag  # REQUIRED - fixes issue #3
        self.rmax = rmax
        self.action_pair_id = action_pair_id
        self.workflow_id = workflow_id
        self.constraints = constraints
        self.r_patience = r_patience or rmax
        self.e_max = e_max
        self.escalate_feedback_to = escalate_feedback_to or []
        self.escalate_feedback_by_guard = escalate_feedback_by_guard or {}
        self.artifact_type = artifact_type or "unknown"
        self.dependency_artifact_contexts = dependency_artifact_contexts or {}
        self.artifact_context = artifact_context or ""

    def execute(self, specification: str = "") -> MockArtifact:
        """Execute the action pair (deterministic fixture mode).
        
        Returns:
            Artifact with fixture content.
        """
        # Generate from action pair
        content = self.action_pair.generator.content

        # Create artifact
        artifact = MockArtifact(
            id=f"{self.workflow_id}_{self.action_pair_id}",
            workflow_id=self.workflow_id,
            content=content,
            status="success",
            artifact_type=self.artifact_type or "fixture",
        )

        # Store in DAG (real behavior - fixes PR #16 issue #3)
        self.artifact_dag.store(artifact)

        return artifact


def create_fixture_action_pair(fixture_content: Dict[str, Any]) -> MockActionPair:
    """Create an ActionPair from fixture content.
    
    Args:
        fixture_content: Dict with 'replicas', 'status', 'edges', etc.
    
    Returns:
        MockActionPair ready to execute.
    """
    return MockActionPair(
        _generator=MockGenerator(content=fixture_content),
        _guard=MockGuard(),
    )
