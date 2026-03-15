# `agent_reviewer`

## Document metadata

- **role_id**: `agent_reviewer`
- **version**: `v1`
- **workflow_scope**: `REVIEWING`

## Responsibility

Review the implemented changes against:

- the approved plan
- architecture constraints
- test evidence

and publish a deterministic review outcome artifact.

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Architecture constraints:
  - `architecture_contract.md`
- Approved planning artifacts:
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`
- Test evidence:
  - `test_report.json`
- Implementation trace:
  - `implementation_summary.md` (if used by the project)

## Outputs (artifacts only)

- `review_result.md`

## Write policy

- **May write**: `review_result.md`
- **Must not write**: implementation code, tests, workflow definitions, domain inputs.

## Prohibitions

- Must not approve without test evidence (unless explicitly accepted as debt with human approval).
- Must not introduce new requirements; findings must map to plan/contract/rules.

## Determinism requirements

`review_result.md` must include:

- outcome: ACCEPTED | ACCEPTED_WITH_DEBT | FAILED
- findings with references to:
  - plan item IDs
  - architecture contract sections
  - test report evidence
- explicit debt items (if any), with ownership and follow-up guidance

## Artifact schemas

- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` â†’ `../artifacts/schemas/design_tradeoffs.schema.md`
- `test_report.json` â†’ `../artifacts/schemas/test_report.schema.json`
- `implementation_summary.md` â†’ `../artifacts/schemas/implementation_summary.schema.md` (if used)
- `review_result.md` â†’ `../artifacts/schemas/review_result.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (records debt acceptance approvals)

## Assumptions / trade-offs

- Human decision remains authoritative; the reviewer provides structured, auditable evidence.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
