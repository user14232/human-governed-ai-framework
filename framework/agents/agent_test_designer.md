# `agent_test_designer`

## Document metadata

- **role_id**: `agent_test_designer`
- **version**: `v1`
- **workflow_scope**: `TEST_DESIGN`

## Responsibility

Design a **test strategy** and concrete test cases based on the approved plan and domain constraints.

## Inputs (read-only)

- Mandatory project inputs:
  - `domain_scope.md`
  - `domain_rules.md`
  - `glossary.md`
  - `source_policy.md`
- Optional project inputs:
  - `evaluation_criteria.md`
  - `goldstandard_knowledge.md`
- Invariants: `../contracts/system_invariants.md`
- Planning artifacts (approved):
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`

## Outputs (artifacts only)

- `test_design.yaml`

## Write policy

- **May write**: `test_design.yaml`
- **Must not write**: implementation code, test code, workflow definitions, domain inputs.

## Prohibitions

- Must not invent requirements beyond the plan and domain rules.
- Must not â€œoptimize awayâ€ required coverage; gaps must be explicit.

## Determinism requirements

- Test cases must be traceable to:
  - plan items (IDs) and/or
  - domain rule references (sections/IDs)

## Artifact schemas

- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` â†’ `../artifacts/schemas/design_tradeoffs.schema.md`
- `test_design.yaml` â†’ `../artifacts/schemas/test_design.schema.yaml`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (records human approval gate)

## Assumptions / trade-offs

- When the plan is ambiguous, the designer documents assumptions explicitly inside `test_design.yaml`.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
