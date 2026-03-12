# `agent_orchestrator`

## Document metadata

- **role_id**: `agent_orchestrator`
- **version**: `v1`
- **workflow_scope**: all delivery states

## Responsibility

Coordinate the delivery workflow **state machine** deterministically:

- validate mandatory project inputs are present
- dispatch the next single-shot role
- enforce â€œartifact-only handoffsâ€
- stop on failed gates / missing approvals

This role does **not** create plans, make domain decisions, or implement code.

## Inputs (read-only)

- Workflow definition: `../workflow/default_workflow.yaml`
- Invariants: `../contracts/system_invariants.md`
- Mandatory project inputs (presence only): see `../contracts/domain_input_contracts.md`
- Approval/decision record (append-only):
  - `decision_log.yaml`
- Existing artifacts (if present):
  - `change_intent.yaml`
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`
  - `arch_review_record.md`
  - `architecture_change_proposal.md` (only if CHANGE_REQUIRED)
  - `branch_status.md`
  - `test_design.yaml`
  - `test_report.json`
  - `review_result.md`
  - `run_metrics.json`

## Outputs (artifacts only)

- Orchestration log / decisions as artifacts (template, optional):
  - `run_metrics.json` (append-only metrics) OR
  - `orchestrator_log.md` (if adopted by project)

## Write policy

- **May write**: orchestration/run metadata artifacts only (no domain content).
- **Must not write**: plans, implementation code, tests, architecture contracts.

## Prohibitions

- Must not loop autonomously.
- Must not proceed past a gate without required artifacts and approvals.
- Must not infer missing inputs or â€œfill inâ€ project artifacts.

## Determinism requirements

- Decisions are based only on:
  - presence/validity of required artifacts
  - explicit approvals recorded by humans in `decision_log.yaml`
  - explicit workflow transitions

## Artifact schemas

- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml`
- `change_intent.yaml` â†’ `../artifacts/schemas/change_intent.schema.yaml`
- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` â†’ `../artifacts/schemas/design_tradeoffs.schema.md`
- `arch_review_record.md` â†’ `../artifacts/schemas/arch_review_record.schema.md`
- `architecture_change_proposal.md` â†’ `../artifacts/schemas/architecture_change_proposal.schema.md`
- `branch_status.md` â†’ `../artifacts/schemas/branch_status.schema.md`
- `test_design.yaml` â†’ `../artifacts/schemas/test_design.schema.yaml`
- `test_report.json` â†’ `../artifacts/schemas/test_report.schema.json`
- `review_result.md` â†’ `../artifacts/schemas/review_result.schema.md`
- `run_metrics.json` â†’ `../artifacts/schemas/run_metrics.schema.json`
- `orchestrator_log.md` â†’ `../artifacts/schemas/orchestrator_log.schema.md` (if adopted by project)

## Assumptions / trade-offs

- â€œApprovalâ€ is represented explicitly in `decision_log.yaml` (append-only, auditable).

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
