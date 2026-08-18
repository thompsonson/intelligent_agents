#!/usr/bin/env python3
"""DS-PDDL parser MVP experiments run against atomicguard-core (read-only)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import textwrap
import traceback
from dataclasses import dataclass
from pathlib import Path

# Point at the dspddl-parser-mvp branch
AG_CORE = Path("/home/mt/Projects/agentia/atomicguard-core/src").resolve()
TESTS = Path("/home/mt/Projects/agentia/atomicguard-core/tests").resolve()
sys.path.insert(0, str(AG_CORE))
sys.path.insert(0, str(TESTS.parent))

# ---------------------------------------------------------------------------
# Test fakes — minimal replicas to avoid coupling to test internals
# ---------------------------------------------------------------------------

from atomicguard.core.domain.interfaces.generator import GeneratorInterface
from atomicguard.core.domain.interfaces.guard import GuardInterface
from atomicguard.core.domain.interfaces.repository import ArtifactDAGInterface
from atomicguard.core.domain.models.artifact import (
    ActionPairId,
    Artifact,
    ArtifactId,
    ArtifactStatus,
    ContextSnapshot,
    WorkflowId,
)
from atomicguard.core.domain.models.context import AmbientEnvironment, Context
from atomicguard.core.domain.models.context_prompts import PromptTemplate
from atomicguard.core.domain.models.guard import GuardResult


class _MemoryArtifactDAG(ArtifactDAGInterface):
    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}

    def store(self, artifact: Artifact) -> str:
        self._artifacts[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def get_artifact(self, artifact_id: str) -> Artifact:
        if artifact_id not in self._artifacts:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return self._artifacts[artifact_id]

    def get_provenance(self, artifact_id: str) -> list[Artifact]:
        chain: list[Artifact] = []
        current_id: str | None = artifact_id
        while current_id is not None:
            a = self._artifacts.get(current_id)
            if a is None:
                break
            chain.insert(0, a)
            current_id = a.previous_attempt_id
        return chain

    def get_latest_for_action_pair(self, action_pair_id: str, workflow_id: str) -> Artifact | None:
        candidates = self.get_all_for_action_pair(action_pair_id, workflow_id)
        return candidates[-1] if candidates else None

    def get_all_for_action_pair(self, action_pair_id: str, workflow_id: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.action_pair_id == action_pair_id and a.workflow_id == workflow_id]

    def get_by_workflow(self, workflow_id: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.workflow_id == workflow_id]

    def get_all(self) -> list[Artifact]:
        return list(self._artifacts.values())


class _MockGenerator(GeneratorInterface):
    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses) if responses else []
        self.call_count = 0

    def generate(self, context: Context, template: PromptTemplate, action_pair_id: str = "unknown",
                 workflow_id: str = "unknown", workflow_ref: str | None = None) -> Artifact:
        import uuid
        from datetime import datetime
        content = self._responses[self.call_count] if self.call_count < len(self._responses) else ""
        self.call_count += 1
        return Artifact(
            artifact_id=ArtifactId(str(uuid.uuid4())), workflow_id=WorkflowId(workflow_id),
            content=content, previous_attempt_id=None, parent_action_pair_id=None,
            action_pair_id=ActionPairId(action_pair_id),
            created_at=datetime.now().isoformat(), attempt_number=self.call_count,
            status=ArtifactStatus.PENDING, guard_result=None,
            context=ContextSnapshot(workflow_id=workflow_id, specification=context.specification,
                                    constraints=context.ambient.constraints, feedback_history=(),
                                    dependency_artifacts=()),
        )


class _StubGuard(GuardInterface):
    def __init__(self, passed: bool = True, feedback: str = "") -> None:
        self._passed = passed
        self._feedback = feedback

    def validate(self, artifact: Artifact, **dependencies: Artifact) -> GuardResult:
        return GuardResult(passed=self._passed, feedback=self._feedback)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

@dataclass
class Result:
    name: str
    passed: bool
    details: str = ""


_results: list[Result] = []


def ok(name: str, details: str = "") -> None:
    _results.append(Result(name, True, details))


def fail(name: str, details: str) -> None:
    _results.append(Result(name, False, details))


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

def _import():
    """Resolve all DSL module imports before experiments."""
    from atomicguard.contrib.dsl.api import parse_dspddl
    from atomicguard.contrib.dsl.errors import DSPDDLError, DSPDDLSyntaxError, DSPDDLValidationError
    from atomicguard.core.domain.models.workflow import WorkflowDefinition
    from atomicguard.core.domain.models.action_pair import ActionPairDefinition
    from atomicguard.core.domain.models.context import APContextEntry
    from atomicguard.core.application.workflow_factory import build_orchestrator
    return (parse_dspddl, DSPDDLError, DSPDDLSyntaxError, DSPDDLValidationError,
            WorkflowDefinition, ActionPairDefinition, APContextEntry, build_orchestrator)


(parse_dspddl, DSPDDLError, DSPDDLSyntaxError, DSPDDLValidationError,
 WorkflowDefinition, ActionPairDefinition, APContextEntry, build_orchestrator) = _import()


# ===========================================================================
# Experiment 1: Parser correctness corpus
# ===========================================================================

def _run_exp1():
    """4 valid + 3 configured + 2 composite + 2 spec + 12 invalid DS-PDDL texts covering all production grammar paths."""

    # ── Valid cases ──────────────────────────────────────────────────────

    # 1a. Minimal workflow
    def v_minimal():
        d, c = parse_dspddl(textwrap.dedent("""\
            (:workflow tdd-basic
                :name "TDD Basic"
                :specification "Build a stack"
                :constraints "Use pytest"
                :rmax 3
                (:action-pair write-tests
                    :context (:role "Python tester" :task "Write tests"
                              :feedback-wrapper "Fix: {feedback}")
                    :generator llm
                    :guard syntax
                    :requires ()))
        """))
        assert d.slug == "tdd-basic"
        assert d.name == "TDD Basic"
        assert d.specification == "Build a stack"
        assert d.rmax == 3
        ap = d.action_pairs[0]
        assert ap.ap_id == "write-tests"
        assert ap.generator == "llm"
        assert ap.guard == "syntax"
        assert ap.requires == ()
        assert c["write-tests"].role == "Python tester"

    # 1b. Three-step escalation workflow
    def v_three_step():
        d, c = parse_dspddl(textwrap.dedent("""\
            (:workflow repair-flow
                :specification "Fix the bug"
                (:action-pair localize
                    :context (:role "E" :task "Find")
                    :generator llm :guard syntax
                    :artifact-type analysis :output-type text)
                (:action-pair patch
                    :context (:role "E" :task "Patch")
                    :generator llm :guard (syntax tests-pass)
                    :requires (localize)
                    :artifact-type patch :output-type diff
                    :r-patience 2 :escalate-feedback-to (localize))
                (:action-pair verify
                    :context (:role "R" :task "Verify")
                    :generator llm :guard tests-pass
                    :requires (patch) :goal true
                    :escalate-feedback-by-guard ((tests-pass (patch localize)))))
        """))
        assert len(d.action_pairs) == 3
        assert d.action_pairs[1].requires == ("localize",)
        assert d.action_pairs[1].r_patience == 2
        assert d.action_pairs[1].escalate_feedback_to == ("localize",)
        assert d.action_pairs[2].goal is True
        assert d.action_pairs[2].escalate_feedback_by_guard == {"tests-pass": ("patch", "localize")}

    # 1c. Effector workflow
    def v_effector():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow restart-flow
                (:action-pair restart
                    :context (:role "SA" :task "Restart")
                    :generator command-template
                    :pre-guard valid-service
                    :effector bash
                    :post-guard (exit-code-zero service-running)))
        """))
        ap = d.action_pairs[0]
        assert ap.pre_guard == "valid-service"
        assert ap.effector == "bash"
        assert ap.guard == ""
        assert ap.guards == ["exit-code-zero", "service-running"]

    # 1d. Composite guard (no effector)
    def v_composite():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow review-flow
                (:action-pair review
                    :context (:role "Reviewer" :task "Review code")
                    :generator llm
                    :guard (syntax lint style)))
        """))
        ap = d.action_pairs[0]
        assert ap.guard == ""
        assert ap.guards == ["syntax", "lint", "style"]

    # 1e. Configured generator
    def v_configured_generator():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow configured-gen
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator (llm :model "gpt-4" :temperature 0)
                    :guard syntax))
        """))
        ap = d.action_pairs[0]
        assert ap.generator == "llm"
        assert ap.generator_config == {"model": "gpt-4", "temperature": 0}

    # 1f. Configured effector
    def v_configured_effector():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow configured-eff
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :pre-guard valid
                    :effector (bash :timeout 30 :shell "/bin/sh")
                    :post-guard ok))
        """))
        ap = d.action_pairs[0]
        assert ap.effector == "bash"
        assert ap.effector_config == {"timeout": 30, "shell": "/bin/sh"}

    # 1g. Configured guard
    def v_configured_guard():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow configured-guard
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :guard (syntax :config (:threshold 80))))
        """))
        ap = d.action_pairs[0]
        assert ap.guard == "syntax"
        assert ap.guards is None
        assert ap.guard_config == {"threshold": 80}

    # 1h. Structured composite guard (composite form)
    def v_structured_composite():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow structured-comp
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :guard (composite
                        :compose sequential
                        :policy any-pass
                        :guards ((syntax) (coverage)))))
        """))
        ap = d.action_pairs[0]
        assert ap.guard == ""
        assert ap.guards is None
        assert ap.guard_tree is not None
        assert ap.guard_tree.kind == "sequential"
        assert ap.guard_tree.policy == "any_pass"
        assert ap.guard_tree.guards == ("syntax", "coverage")

    # 1i. Sequential inline composite guard
    def v_sequential_inline():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow seq-inline
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :guard (sequential :policy any-pass syntax tests-pass)))
        """))
        ap = d.action_pairs[0]
        assert ap.guard == ""
        assert ap.guards is None
        assert ap.guard_tree is not None
        assert ap.guard_tree.kind == "sequential"
        assert ap.guard_tree.policy == "any_pass"
        assert ap.guard_tree.guards == ("syntax", "tests-pass")

    # 1j. File spec source
    def v_file_spec():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow file-spec
                :specification (file "spec.md")
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :guard syntax))
        """))
        assert d.specification == ""
        assert d.spec_ref is not None
        assert d.spec_ref.kind == "file"
        assert d.spec_ref.path == "spec.md"
        assert d.spec_ref.glob is None

    # 1k. Folder spec source with glob
    def v_folder_spec():
        d, _c = parse_dspddl(textwrap.dedent("""\
            (:workflow folder-spec
                :specification (folder "docs" :glob "*.md")
                (:action-pair a
                    :context (:role "r" :task "t")
                    :generator llm
                    :guard syntax))
        """))
        assert d.specification == ""
        assert d.spec_ref is not None
        assert d.spec_ref.kind == "folder"
        assert d.spec_ref.path == "docs"
        assert d.spec_ref.glob == "*.md"

    for name, fn in [("1a-minimal", v_minimal), ("1b-three-step", v_three_step),
                     ("1c-effector", v_effector), ("1d-composite", v_composite),
                     ("1e-configured-generator", v_configured_generator),
                     ("1f-configured-effector", v_configured_effector),
                     ("1g-configured-guard", v_configured_guard),
                     ("1h-structured-composite", v_structured_composite),
                     ("1i-sequential-inline", v_sequential_inline),
                     ("1j-file-spec", v_file_spec),
                     ("1k-folder-spec", v_folder_spec)]:
        try:
            fn()
            ok(f"exp1: Valid corpus — {name}")
        except Exception as e:
            fail(f"exp1: Valid corpus — {name}", f"{type(e).__name__}: {e}")

    # ── Invalid cases ────────────────────────────────────────────────────

    cases = [
        ("duplicate-ap-id",
         "Duplicate action pair id",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax) (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax))"""),
        ("missing-generator",
         "is missing :generator",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :guard syntax))"""),
        ("unresolved-requires",
         "references unknown action pair",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax :requires (missing)))"""),
        ("mixed-guard-effector",
         "cannot mix :guard with :effector",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax :effector bash :pre-guard v :post-guard o))"""),
        ("effector-no-preguard",
         "requires :pre-guard and :post-guard",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :pre-guard v :effector bash))"""),
        ("unknown-workflow-field",
         "Unknown workflow field",
         """(:workflow bad :invalid-field "x" (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax))"""),
        ("duplicate-workflow-field",
         "Duplicate field in workflow",
         """(:workflow bad :name "a" :name "b" (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax))"""),
        ("missing-context",
         "is missing :context",
         """(:workflow bad (:action-pair a :generator llm :guard syntax))"""),
        ("no-action-pairs",
         "must define at least one action pair",
         """(:workflow bad :name "empty")"""),
        ("rpatience-over-rmax",
         "invalid r_patience",
         """(:workflow bad :rmax 3 (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax :r-patience 4))"""),
        ("composite-bad-kind",
         "unsupported composite guard kind",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard (composite :compose xor :policy all-pass :guards ((syntax) (coverage)))))"""),
        ("composite-bad-policy",
         "Unsupported composite guard policy",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard (sequential :policy maybe-pass syntax tests-pass)))"""),
    ]

    for name, expected_msg, source in cases:
        source = textwrap.dedent(source)
        # unknown-workflow-field is now caught at grammar level (DSPDDLSyntaxError)
        is_syntax_expected = name in ("unknown-workflow-field",)
        try:
            parse_dspddl(source)
            fail(f"exp1: Invalid corpus — {name}", f"Expected {expected_msg}, no error raised")
        except (DSPDDLSyntaxError) as e:
            if is_syntax_expected:
                ok(f"exp1: Invalid corpus — {name}", f"[grammar-level] {e}")
            else:
                fail(f"exp1: Invalid corpus — {name}", f"Expected DSPDDLValidationError, got DSPDDLSyntaxError: {e}")
        except DSPDDLValidationError as e:
            if expected_msg.lower() in str(e).lower():
                ok(f"exp1: Invalid corpus — {name}", f"matched: {e}")
            else:
                fail(f"exp1: Invalid corpus — {name}", f"Expected '{expected_msg}', got '{e}'")
        except Exception as e:
            fail(f"exp1: Invalid corpus — {name}", f"Expected DSPDDLValidationError, got {type(e).__name__}: {e}")


# ===========================================================================
# Experiment 2: Dataclass equivalence
# ===========================================================================

def _run_exp2():
    """Hand-built vs parsed equality check using frozen dataclass ==."""
    source = textwrap.dedent("""\
        (:workflow equiv-test
            :name "Equiv Test"
            :specification "Test equality"
            :constraints "None"
            :rmax 5
            (:action-pair step-a
                :context (:role "ROLE" :task "TASK" :constraints "CTX"
                          :feedback-wrapper "FW" :escalation-feedback-wrapper "EFW"
                          :feedback-mode inline :artifact-context "AC")
                :generator llm
                :guard syntax
                :requires (step-b)
                :artifact-type my-type
                :output-type my-output
                :r-patience 3
                :e-max 2
                :escalate-feedback-to (step-b)
                :group g1
                :goal false)
            (:action-pair step-b
                :context (:role "R2" :task "T2")
                :generator llm
                :guard (g1 g2)
                :goal true))
    """)

    parsed_def, parsed_ctx = parse_dspddl(source)

    hand_built_ctx = {
        "step-a": APContextEntry(
            ap_id="step-a", role="ROLE", constraints="CTX", task="TASK",
            feedback_wrapper="FW", escalation_feedback_wrapper="EFW",
            feedback_mode="inline", artifact_context="AC",
        ),
        "step-b": APContextEntry(
            ap_id="step-b", role="R2", constraints="", task="T2",
        ),
    }
    hand_built_def = WorkflowDefinition(
        slug="equiv-test", name="Equiv Test", specification="Test equality",
        constraints="None", rmax=5, action_pairs=(
            ActionPairDefinition(
                ap_id="step-a", generator="llm", guard="syntax", guards=None,
                requires=("step-b",), artifact_type="my-type", output_type="my-output",
                r_patience=3, e_max=2, escalate_feedback_to=("step-b",),
                group="g1", goal=False,
            ),
            ActionPairDefinition(
                ap_id="step-b", generator="llm", guard="", guards=["g1", "g2"],
                goal=True,
            ),
        ),
    )

    try:
        assert parsed_def == hand_built_def, f"WorkflowDefinition mismatch"
        ok("exp2: WorkflowDefinition equality")
    except AssertionError as e:
        import dataclasses as _dc
        diffs = []
        for _f in _dc.fields(parsed_def):
            pv, hv = getattr(parsed_def, _f.name), getattr(hand_built_def, _f.name)
            if pv != hv:
                diffs.append(f"WF.{_f.name}: parsed={pv!r} hand={hv!r}")
        for i, (p, h) in enumerate(zip(parsed_def.action_pairs, hand_built_def.action_pairs)):
            for _f in _dc.fields(p):
                pv, hv = getattr(p, _f.name), getattr(h, _f.name)
                if pv != hv:
                    diffs.append(f"AP[{i}].{_f.name}: parsed={pv!r} hand={hv!r}")
        fail("exp2: WorkflowDefinition equality", "; ".join(diffs) if diffs else str(e))

    try:
        assert parsed_ctx == hand_built_ctx, f"APContextEntry dict mismatch"
        ok("exp2: APContextEntry equality")
    except AssertionError as e:
        fail("exp2: APContextEntry equality", str(e))


# ===========================================================================
# Experiment 3: Orchestrator build smoke
# ===========================================================================

def _run_exp3():
    """Parse then pass to build_orchestrator with fake registries."""

    # 3a. Minimal workflow
    source_min = textwrap.dedent("""\
        (:workflow smoke-test
            (:action-pair write-tests
                :context (:role "T" :task "Write tests")
                :generator llm
                :guard syntax)
            (:action-pair write-code
                :context (:role "D" :task "Write code")
                :generator llm
                :guard (syntax tests-pass)
                :requires (write-tests)))
    """)
    def_min, ctx_min = parse_dspddl(source_min)
    reg = {"llm": _MockGenerator(responses=["ok"])}
    guard_reg = {"syntax": _StubGuard(passed=True), "tests-pass": _StubGuard(passed=True)}

    try:
        orch = build_orchestrator(def_min, ctx_min, reg, guard_reg, _MemoryArtifactDAG())
        assert len(orch._steps) == 2
        ok("exp3: Minimal workflow builds")
    except Exception as e:
        fail("exp3: Minimal workflow builds", f"{type(e).__name__}: {e}")

    # 3b. Effector workflow
    source_eff = textwrap.dedent("""\
        (:workflow effector-smoke
            (:action-pair restart
                :context (:role "SA" :task "Restart")
                :generator cmd
                :pre-guard validate
                :effector bash
                :post-guard check))
    """)
    def_eff, ctx_eff = parse_dspddl(source_eff)
    eff_reg = {"cmd": _MockGenerator(["restart"]), "bash": _StubGuard(passed=True)}
    eff_guard_reg = {"validate": _StubGuard(passed=True), "check": _StubGuard(passed=True)}

    try:
        orch = build_orchestrator(def_eff, ctx_eff, eff_reg, eff_guard_reg,
                                  _MemoryArtifactDAG(), effector_registry={"bash": _StubGuard(passed=True)})
        assert len(orch._steps) == 1
        step = orch._steps[0]
        assert step.r_patience is None
        ok("exp3: Effector workflow builds")
    except Exception as e:
        fail("exp3: Effector workflow builds", f"{type(e).__name__}: {e}")

    # 3c. Escalation params propagate
    source_esc = textwrap.dedent("""\
        (:workflow esc-smoke
            :rmax 7
            (:action-pair a
                :context (:role "R" :task "T")
                :generator llm :guard g1
                :r-patience 4 :e-max 3
                :escalate-feedback-to (b))
            (:action-pair b
                :context (:role "R" :task "T")
                :generator llm :guard g1))
    """)
    def_esc, ctx_esc = parse_dspddl(source_esc)
    esc_guard_reg = {"g1": _StubGuard(passed=True)}
    try:
        orch = build_orchestrator(def_esc, ctx_esc, reg, esc_guard_reg, _MemoryArtifactDAG())
        step_a = orch._steps[0]
        assert step_a.r_patience == 4, f"Expected r_patience=4, got {step_a.r_patience}"
        assert step_a.e_max == 3, f"Expected e_max=3, got {step_a.e_max}"
        assert step_a.escalate_feedback_to == ("b",)
        ok("exp3: Escalation params propagate")
    except Exception as e:
        fail("exp3: Escalation params propagate", f"{type(e).__name__}: {e}")


# ===========================================================================
# Experiment 4: Core boundary check
# ===========================================================================

def _run_exp4():
    """Import api and verify only expected modules leak."""
    import atomicguard.contrib.dsl.api  # noqa: F811, F401

    contrib_modules = [m for m in sys.modules if "atomicguard.contrib" in m]
    unexpected = [m for m in contrib_modules
                  if not (m == "atomicguard.contrib"
                          or m.startswith("atomicguard.contrib.dsl"))]
    if unexpected:
        fail("exp4: Core boundary", f"unexpected contrib imports: {unexpected}")
    else:
        ok("exp4: Core boundary", f"Only contrib.dsl modules loaded: {contrib_modules}")


# ===========================================================================
# Experiment 5: Package data check
# ===========================================================================

def _run_exp5():
    """Verify dspddl.lark is accessible via importlib.resources."""
    from importlib.resources import files

    try:
        grammar = files("atomicguard.contrib.dsl").joinpath("dspddl.lark").read_text()
        assert len(grammar) > 50, "Grammar too short"
        assert "KEYWORD" in grammar, "Missing KEYWORD rule"
        ok("exp5: Package data", f"Lark grammar read ({len(grammar)} chars)")
    except Exception as e:
        fail("exp5: Package data", f"{type(e).__name__}: {e}")


# ===========================================================================
# Experiment 6: Error quality spike
# ===========================================================================

def _run_exp6():
    """Feed malformed inputs and assess error message quality."""

    cases = [
        ("6a-unterminated", "Unterminated s-expression",
         """(:workflow x"""),
        ("6b-wrong-root", "Wrong root form",
         """(invalid-root)"""),
        ("6c-unbalanced-parens", "Unbalanced parentheses",
         """(:workflow x (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax)"""),
        ("6d-ap-no-fields", "Action pair with no fields",
         """(:workflow bad (:action-pair a))"""),
        ("6e-e-max-zero", "e_max below minimum (0)",
         """(:workflow bad (:action-pair a :context (:role "r" :task "t") :generator llm :guard syntax :e-max 0))"""),
    ]

    for case_id, label, source in cases:
        try:
            parse_dspddl(textwrap.dedent(source))
            fail(f"exp6: {case_id} — {label}", "No error raised")
        except DSPDDLValidationError as e:
            msg = str(e)
            has_location = ":" in msg and any(c.isdigit() for c in msg[:msg.index(":")+2]) if ":" in msg else False
            has_suggestion = any(w in msg.lower() for w in ["expected", "must", "use", "try", "missing"])
            tags = []
            if has_location:
                tags.append("has location")
            if has_suggestion:
                tags.append("has suggestion")
            quality = "actionable" if has_location and has_suggestion else "needs improvement" if has_suggestion else "cryptic"
            ok(f"exp6: {case_id} — {label}", f"[{quality}] [{', '.join(tags)}] {msg}")
        except Exception as e:
            msg = str(e)
            has_location = "line" in msg.lower() or "col" in msg.lower()
            has_suggestion = False
            quality = "actionable" if has_location else "cryptic"
            ok(f"exp6: {case_id} — {label}", f"[{quality}] {type(e).__name__}: {msg}")


# ===========================================================================
# Main runner
# ===========================================================================

def main() -> None:
    print("=" * 72)
    print("  DS-PDDL Parser MVP — Experiment Report")
    print(f"  Branch: feat/dspddl-parser-mvp  |  Target: {AG_CORE}")
    print("=" * 72)
    print()

    _run_exp1()
    _run_exp2()
    _run_exp3()
    _run_exp4()
    _run_exp5()
    _run_exp6()

    print()
    print("-" * 72)
    passed = sum(1 for r in _results if r.passed)
    total = len(_results)
    print(f"  Summary: {passed}/{total} passed, {total - passed} failed")
    print()

    # Group results by status
    for r in _results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"  [{mark}] {r.name}")
        if r.details:
            for line in r.details.split("\n"):
                print(f"         {line}")

    if total - passed > 0:
        print()
        print("  FAILURES:")
        for r in _results:
            if not r.passed:
                print(f"    - {r.name}: {r.details}")


if __name__ == "__main__":
    main()
