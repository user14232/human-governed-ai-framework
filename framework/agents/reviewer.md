# `reviewer`

## Document metadata

- **role_id**: `reviewer`
- **version**: `v1`
- **workflow_scope**: `REVIEWING`

## Responsibility

The reviewer operates in two contexts within the delivery workflow:

**Architecture review (ARCH_CHECK state)**
Check the implementation plan for compliance with the architecture contract. Produce `arch_review_record.md` with an explicit PASS or CHANGE_REQUIRED outcome. If CHANGE_REQUIRED, produce `architecture_change_proposal.md`.

**Final review (REVIEWING state)**
Evaluate the complete change against the approved plan, architecture constraints, and test evidence. Produce `review_result.md` with an explicit ACCEPTED, ACCEPTED_WITH_DEBT, or FAILED outcome.

The reviewer must not approve changes that violate the architecture contract. The reviewer must not introduce new requirements. All findings must cite explicit plan items, contract sections, or test evidence.

## Inputs

- `architecture_contract.md`
- `domain_rules.md`
- `implementation_plan.yaml`
- `design_tradeoffs.md`
- `arch_review_record.md` (required for final review; produced by reviewer at ARCH_CHECK)
- `test_report.json` (required for final review)
- `implementation_summary.md` (if available)

## Outputs

- `arch_review_record.md`
- `architecture_change_proposal.md` (only if arch review outcome is CHANGE_REQUIRED)
- `review_result.md`

## Write policy

- **May write**: `arch_review_record.md`, `architecture_change_proposal.md`, `review_result.md`
- **Must not write**: implementation code, tests, workflow definitions, domain inputs.

## Prohibitions

- Must not approve a plan that violates `architecture_contract.md`.
- Must not approve a final review without test evidence (unless explicitly accepted as debt with human approval in `decision_log.yaml`).
- Must not introduce new requirements; findings must map to plan items, contract sections, or test results.
- Must not edit code directly to fix architecture issues.

## Determinism requirements

`arch_review_record.md` must include:
- outcome: PASS or CHANGE_REQUIRED
- findings with explicit references to contract sections

`review_result.md` must include:
- outcome: ACCEPTED | ACCEPTED_WITH_DEBT | FAILED
- findings with references to plan item IDs, architecture contract sections, and test report evidence
- explicit debt items (if any), with ownership and follow-up guidance

## Artifact schemas

- `implementation_plan.yaml` → `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` → `../artifacts/schemas/design_tradeoffs.schema.md`
- `arch_review_record.md` → `../artifacts/schemas/arch_review_record.schema.md`
- `architecture_change_proposal.md` → `../artifacts/schemas/architecture_change_proposal.schema.md`
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`
- `implementation_summary.md` → `../artifacts/schemas/implementation_summary.schema.md`
- `review_result.md` → `../artifacts/schemas/review_result.schema.md`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml`

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-15 | Consolidated from agent_architecture_guardian.md and agent_reviewer.md; role_id simplified per four-role model. |
