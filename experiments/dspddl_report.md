DS-PDDL Parser MVP — Experiment Report
========================================
Branch: feat/dspddl-parser-mvp
Package: atomicguard.contrib.dsl (moved from atomicguard.core.dsl)
Target: /home/mt/Projects/agentia/atomicguard-core
Lark:   1.3.1
Run:    26/26 passed, 0 failed


Experiment Results
------------------

[PASS] Exp 1 — Parser correctness corpus   (14/14)
  - 4 valid workflows: minimal, three-step escalation, effector, composite guard
    → All field assertions pass (slug, rmax, generator, guard, requires,
      escalate_feedback_to, escalate_feedback_by_guard, pre_guard, effector,
      guards list)
  - 10 invalid workflows: duplicate AP id, missing generator, unresolved
    requires, mixed guard/effector, effector without pre-guard, unknown
    workflow field, duplicate workflow field, missing context, empty workflow,
    r_patience >= rmax
    → All raise DSPDDLValidationError with expected substrings

[PASS] Exp 2 — Dataclass equivalence       (2/2)
  - WorkflowDefinition equality via frozen dataclass __eq__: matches
  - APContextEntry dict equality: matches
  - Every field on every AP checked: no drift between parsed and hand-built

[PASS] Exp 3 — Orchestrator build smoke    (3/3)
  - Minimal 2-AP workflow → orchestrator._steps length 2
  - Effector workflow → pre_guard/effector/post_guard resolved, no errors
  - Escalation params → r_patience=4, e_max=3, escalate_feedback_to=("b",)
    propagated to WorkflowStep correctly

[PASS] Exp 4 — Core boundary               (1/1)
  - import atomicguard.contrib.dsl.api
  - No modules outside atomicguard.contrib.dsl.* leaked
  - Imports: {contrib.dsl.*, domain.models.*} only

[PASS] Exp 5 — Package data                (1/1)
  - files("atomicguard.contrib.dsl").joinpath("dspddl.lark").read_text()
  → 416 chars, includes KEYWORD rule

[PASS] Exp 6 — Error quality spike         (5/5)
  - 6a: unterminated sexpr  → [actionable]   line:col + expected tokens
  - 6b: wrong root form     → [needs improvement] has suggestion, no line#
  - 6c: unbalanced parens   → [actionable]   line:col + expected tokens
  - 6d: AP with no fields   → [needs improvement] has suggestion, no line#
  - 6e: e_max=0             → [needs improvement]  says invalid, now states range


Findings & Proposed Fixes
-------------------------

### 1. e_max validation error is cryptic

File:           src/atomicguard/contrib/dsl/validation.py:41-43
Error message:  "Action pair 'a' has invalid e_max: 0."
Problem:        Doesn't state the required range (>= 1).

Proposed fix:

    if ap_def.e_max < 1:
        raise DSPDDLValidationError(
            f"Action pair '{ap_def.ap_id}' has invalid e_max: "
            f"{ap_def.e_max}. Expected e_max >= 1."
        )

The range is defined by ActionPairDefinition's default e_max: int = 1,
but the error should tell the user explicitly.

**Status:** ✅ FIXED — now reads `Expected e_max >= 1.`

### 2. Validation errors lack input position

Files:
- src/atomicguard/contrib/dsl/translator.py:64-65   (root form check)
- src/atomicguard/contrib/dsl/translator.py:115-116 (AP id check)
- src/atomicguard/contrib/dsl/validation.py:13-15   (duplicate AP id)

Problem:
- Lark syntax errors (exp6a, exp6c) include line:column — good.
- DSL validation errors (exp6b, exp6d, exp6e) never reference the input
  position because the s-expression parser discards token positions.

Assessment:
- For a workflow DSL where individual forms are 3-15 lines, the current
  error messages are sufficient for a workflow author to locate the issue.
- If desired, the ParsedDocument AST could carry token positions (Lark
  token `.line` / `.column`) and pass them through to DSPDDLValidationError.
  This is a follow-up enhancement, not a release blocker.

### 3. No structural issues found

- All 10 invalid corpus cases are caught with clear error messages.
- Orchestrator build works without factory changes — the DSL is compatible
  with the existing build_orchestrator() signature.
- Core boundary is clean — no contrib module outside contrib.dsl leaked via the API.
- Package data setup (pyproject.toml) is correct — grammar loads via
  importlib.resources without errors.
