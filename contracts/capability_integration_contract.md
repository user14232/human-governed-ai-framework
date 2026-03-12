# Capability integration contract (v1)

## Responsibility

Define **how project-provided capability agents integrate into the framework lifecycle**.

`capabilities.yaml` defines the capability interface contracts (inputs, outputs, constraints).
This document defines **when, where, and how** capabilities may be invoked within a workflow,
and what blocking semantics apply to their results.

## Input contract

- **Inputs**: `capabilities.yaml`, `workflow/default_workflow.yaml`, `artifacts/schemas/`
- **Readers**: Runtime implementers, `agent_orchestrator`, project capability providers, humans.

## Output contract

- **Outputs**: Normative rules for capability invocation and result handling.

## Non-negotiables

- Capabilities may not alter workflow state directly.
- Capabilities may not produce governance artifacts (`decision_log.yaml`, `implementation_plan.yaml`, etc.).
- Capability outputs are advisory unless explicitly declared as gate-blocking by this contract.
- A failed or absent capability invocation must be recorded; it must not be silently ignored.

---

## 1. Capability classification

### 1.1 Advisory capabilities (default)

A capability whose output is not required for any workflow gate to pass.

- The workflow may advance without a capability result.
- The absence of a capability result must be logged (event type `artifact.validation_failed`
  or a note in `run_metrics.json`).
- Examples: `domain_explanation` is always advisory.

### 1.2 Gate-blocking capabilities (explicitly declared)

A capability that, when invoked, must produce a satisfactory result for a workflow gate to pass.

Gate-blocking capability invocations must be declared explicitly in a project's
`architecture_contract.md` or in a project-level workflow extension.
The framework does not make any capability gate-blocking by default.

- A `domain_validation` capability may be declared gate-blocking for the `PLANNING → ARCH_CHECK`
  transition by the project.
- When gate-blocking: a `validation_result.md` with a failing outcome blocks the gate, same as
  a missing required artifact.

---

## 2. Invocation rules

### 2.1 When capabilities may be invoked

| Capability | Typical invocation point | May be invoked at |
| --- | --- | --- |
| `domain_validation` | PLANNING, ARCH_CHECK, TEST_DESIGN, REVIEWING | Any state where an artifact is being assessed |
| `domain_explanation` | Any state | Any state |

### 2.2 Who may invoke

- `agent_orchestrator` may invoke any registered capability.
- Any agent role may invoke `domain_explanation` as a read-only consultation.
- No agent role may invoke a capability and pass its output as a governance artifact.

### 2.3 Invocation record

Every capability invocation must be recorded in `run_metrics.json` as an invocation record
(see `artifacts/schemas/run_metrics.schema.json`) with:

- `agent_role`: the capability identifier (e.g., `domain_validation`)
- `workflow_state`: state at time of invocation
- `input_artifacts`: the artifacts passed to the capability
- `output_artifacts`: the produced `validation_result.md` or `explanation.md`
- `outcome`: `completed | blocked | failed`

---

## 3. Output artifact contracts

| Capability | Output artifact | Schema |
| --- | --- | --- |
| `domain_validation` | `validation_result.md` | `artifacts/schemas/validation_result.schema.md` |
| `domain_explanation` | `explanation.md` | `artifacts/schemas/explanation.schema.md` |

Output artifacts are placed in the run directory under `runs/<run_id>/artifacts/`.

---

## 4. Failure handling

| Scenario | Required behavior |
| --- | --- |
| Capability invocation fails to produce output | Record failed invocation; if gate-blocking, block the gate |
| Capability produces output with validation errors | If advisory: log and continue; if gate-blocking: block the gate |
| Capability is not registered for the project | Skip invocation; record as skipped in invocation record |
| Capability produces ambiguous result | Treat as failed; do not infer a pass |

---

## 5. Capability registry

Projects must declare which capabilities they provide in a `project_capabilities.yaml` file.
See `artifacts/schemas/capability_registry.schema.yaml` for the required format.

If no `project_capabilities.yaml` is present, the framework treats all capabilities as absent
(no invocations occur; advisory gaps are logged).

---

## Assumptions and trade-offs

- The framework intentionally keeps capabilities advisory by default to prevent project
  validation logic from silently blocking workflows without explicit human intent.
- Gate-blocking capability invocations require explicit project declaration, not framework assumption.
- This contract governs integration only; capability logic is project-owned and must
  be deterministic and explainable per `capabilities.yaml`.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial version. Defines capability classification, invocation rules, output contracts, failure handling, and registry reference. |
