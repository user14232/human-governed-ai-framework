# `agent_orchestrator` (v1)

## Responsibility

Coordinate the delivery workflow **state machine** deterministically:

- validate mandatory project inputs are present
- dispatch the next single-shot role
- enforce “artifact-only handoffs”
- stop on failed gates / missing approvals

This role does **not** create plans, make domain decisions, or implement code.

## Inputs (read-only)

- Workflow definition: `../workflow/default_workflow.yaml`
- Invariants: `../system_invariants.md`
- Mandatory project inputs (presence only): see `../domain_input_contracts.md`
- Approval/decision record (append-only):
  - `decision_log.yaml`
- Existing artifacts (if present):
  - `change_intent.yaml`
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`
  - `test_design.yaml`
  - `test_report.json`
  - `review_result.md`
  - `run_metrics.json`
  - `architecture_change_proposal.md` (optional)

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
- Must not infer missing inputs or “fill in” project artifacts.

## Determinism requirements

- Decisions are based only on:
  - presence/validity of required artifacts
  - explicit approvals recorded by humans in `decision_log.yaml`
  - explicit workflow transitions

## Artifact schemas

- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml`
- `change_intent.yaml` → `../artifacts/schemas/change_intent.schema.yaml`
- `implementation_plan.yaml` → `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` → `../artifacts/schemas/design_tradeoffs.schema.md`
- `test_design.yaml` → `../artifacts/schemas/test_design.schema.yaml`
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`
- `review_result.md` → `../artifacts/schemas/review_result.schema.md`
- `run_metrics.json` → `../artifacts/schemas/run_metrics.schema.json`
- `architecture_change_proposal.md` → `../artifacts/schemas/architecture_change_proposal.schema.md`
- `orchestrator_log.md` → `../artifacts/schemas/orchestrator_log.schema.md` (if adopted by project)

## Assumptions / trade-offs

- “Approval” is represented explicitly in `decision_log.yaml` (append-only, auditable).
