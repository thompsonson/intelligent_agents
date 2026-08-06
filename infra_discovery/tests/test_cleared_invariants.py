"""Property-based tests for `D1`/`D2`: `cleared`'s core invariants.

Per D-004: property-based testing starts at the build-sequence step a
universal claim first appears in - `D1`/`D2` are exactly that shape for
step5_agent_program.md's Step 2 (`requires`/`SWEEP-CLEARED`), the same
discipline test_bidirectional_discovery.py already applied to `F-001`.

- D1 (monotonic clearance): once a subject enters `cleared`, it never
  leaves, across arbitrary `requires` graphs.
- D2 (cycle-safe clearance): `SWEEP-CLEARED` never crashes or hangs on a
  cyclic `requires` declaration (F-002's original failing case - the
  recursive `CLEARED(subject)` pseudocode would stack-overflow); cyclic
  members simply never enter `cleared`.

Mirrors test_bidirectional_discovery.py's strategy style directly.
"""

from datetime import datetime, timezone

from hypothesis import given, settings, strategies as st
import pytest

from infra_discovery.agents.core.domain import NodeId, Facet
from infra_discovery.agents.core.belief_state import BeliefState


domain_strategy = st.sampled_from(["github_actions", "kubernetes", "gcp"])
kind_strategy = st.sampled_from(["job", "Deployment", "Pod", "CloudRun_service"])
id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz-", min_size=1, max_size=20
)


def node_id_strategy():
    """Generate arbitrary NodeIds."""
    return st.builds(NodeId, domain=domain_strategy, kind=kind_strategy, id=id_strategy)


def _sense(state: BeliefState, subject: NodeId) -> None:
    """Give `subject` a facet, so it enters RECORDED-SUBJECTS()."""
    state.record(
        subject,
        {
            "probe": Facet(
                value=True, observed_at=datetime.now(timezone.utc), sensed_by="test"
            )
        },
    )


@st.composite
def requires_graph(draw, max_nodes=8):
    """An arbitrary set of NodeIds, each with a `requires` tuple drawn from
    the same set - deliberately allows self-requires and mutual cycles,
    since D2 is specifically about surviving those, not avoiding them.
    """
    nodes = draw(
        st.lists(node_id_strategy(), min_size=1, max_size=max_nodes, unique=True)
    )
    requires = {
        n: tuple(
            draw(st.lists(st.sampled_from(nodes), max_size=len(nodes), unique=True))
        )
        for n in nodes
    }
    return nodes, requires


class TestD1MonotonicClearance:
    """D1: cleared only grows, for any requires graph."""

    @given(graph=requires_graph())
    @settings(max_examples=100)
    def test_cleared_never_shrinks_across_repeated_sweeps(self, graph):
        nodes, requires = graph
        state = BeliefState()
        for n in nodes:
            _sense(state, n)
            state.record_requires(n, requires[n])

        previous = set()
        # A few sweeps past the fixed point - sweep_cleared() is meant to be
        # safe (and a no-op) to call repeatedly, every turn of the flat loop.
        for _ in range(len(nodes) + 3):
            state.sweep_cleared()
            assert previous <= state.cleared, (
                f"cleared shrank: {previous} -> {state.cleared}"
            )
            previous = set(state.cleared)

    @given(graph=requires_graph())
    @settings(max_examples=100)
    def test_cleared_monotonic_under_incremental_recording(self, graph):
        """The realistic shape: sweep_cleared() called every turn, as more
        subjects get sensed one at a time (not all-at-once)."""
        nodes, requires = graph
        state = BeliefState()

        previous = set()
        for n in nodes:
            _sense(state, n)
            state.record_requires(n, requires[n])
            state.sweep_cleared()
            assert previous <= state.cleared, (
                f"cleared shrank after recording {n!r}: {previous} -> {state.cleared}"
            )
            previous = set(state.cleared)

    def test_unknowable_subject_clears_immediately(self):
        """RECORD-UNKNOWABLE propagates: a permanently-failed subject still
        counts as cleared (per step0_schema.md's `RECORD-UNKNOWABLE`/
        `RECORD-BLOCKED` propagation row), unblocking anything requiring it."""
        state = BeliefState()
        a = NodeId("github_actions", "job", "a")
        b = NodeId("github_actions", "job", "b")
        _sense(state, a)
        _sense(state, b)
        state.record_requires(b, (a,))
        state.record_unknowable(a)

        state.sweep_cleared()
        assert a in state.cleared
        assert b in state.cleared


class TestD2CycleSafeClearance:
    """D2: SWEEP-CLEARED never crashes/hangs on a cyclic requires graph;
    cyclic members never clear."""

    @given(graph=requires_graph())
    @settings(max_examples=100, deadline=None)
    def test_sweep_terminates_and_stays_sound(self, graph):
        """No exception (would be a stack overflow under the original
        recursive CLEARED(subject) pseudocode F-002 replaced), and every
        cleared subject's requires are themselves all cleared."""
        nodes, requires = graph
        state = BeliefState()
        for n in nodes:
            _sense(state, n)
            state.record_requires(n, requires[n])

        state.sweep_cleared()  # must not raise, must return

        for n in state.cleared:
            assert all(r in state.cleared for r in requires[n]), (
                f"{n!r} cleared without all requires cleared: {requires[n]}"
            )

    def test_self_requires_never_clears(self):
        """A subject requiring itself can never satisfy `all(r in cleared)`
        before it's in cleared - the trivial 1-cycle."""
        state = BeliefState()
        a = NodeId("github_actions", "job", "a")
        _sense(state, a)
        state.record_requires(a, (a,))

        for _ in range(5):
            state.sweep_cleared()

        assert a not in state.cleared

    def test_mutual_two_cycle_never_clears(self):
        """A requires B, B requires A, neither has any other path to
        clearance - both must stay out of cleared forever."""
        state = BeliefState()
        a = NodeId("github_actions", "job", "a")
        b = NodeId("kubernetes", "Deployment", "b")
        _sense(state, a)
        _sense(state, b)
        state.record_requires(a, (b,))
        state.record_requires(b, (a,))

        for _ in range(5):
            state.sweep_cleared()

        assert a not in state.cleared
        assert b not in state.cleared

    def test_cycle_with_external_anchor_clears_the_anchor_only(self):
        """A <-> B cycle, plus C (requires=()) that neither A nor B require -
        C must clear, A/B must not, proving the cycle doesn't poison
        unrelated subjects."""
        state = BeliefState()
        a = NodeId("github_actions", "job", "a")
        b = NodeId("github_actions", "job", "b")
        c = NodeId("github_actions", "job", "c")
        _sense(state, a)
        _sense(state, b)
        _sense(state, c)
        state.record_requires(a, (b,))
        state.record_requires(b, (a,))
        state.record_requires(c, ())

        state.sweep_cleared()

        assert c in state.cleared
        assert a not in state.cleared
        assert b not in state.cleared
