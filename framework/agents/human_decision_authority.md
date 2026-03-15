# `human_decision_authority`

## Document metadata

- **role_id**: `human_decision_authority`
- **version**: `v1`
- **workflow_scope**: all approval gates (delivery, improvement cycle, release)

## Responsibility

Make explicit **approval / rejection / deferral decisions** required by the workflow.

This is a **system actor** (meta-role), not an autonomous agent:

- it produces decision records as artifacts
- it does not modify technical artifacts directly

## Inputs (read-only)

- Workflow definitions:
  - `../workflow/default_workflow.yaml`
  - `../workflow/improvement_cycle.yaml`
- Invariants: `../contracts/system_invariants.md`
- Decision requests (artifacts referenced by the orchestrator), typically:
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`
  - `test_design.yaml`
  - `review_result.md`
  - `improvement_proposal.md`
  - `architecture_change_proposal.md` (if applicable)

## Outputs (artifacts only)

- `decision_log.yaml` (append-only decisions/approvals)

## Write policy

- **May write**: `decision_log.yaml` only.
- **Must not write**: plans, code, tests, workflows, domain inputs, architecture contract text.

## Prohibitions

- Must not modify technical artifacts directly (approval is recorded, not applied).
- Must not approve scope expansion implicitly; approvals must reference explicit artifacts/IDs.
- Must not bypass workflow gates; decisions must match the workflowâ€™s required approval points.

## Determinism requirements

Every decision entry in `decision_log.yaml` must:

- reference the exact artifact(s) being decided on (filenames + IDs if available)
- use a stable `decision_id` and record `human_identity` and `timestamp`
- be auditable and unambiguous (no implied approvals)

## Assumptions / trade-offs

- Human identity is recorded as a string (no IAM coupling at framework level).
- Projects may implement stricter identity/approval mechanisms, but must preserve the artifact audit trail.
- `decision_log.yaml` is the **sole normative approval source**. Any "Decision reference" sections
  embedded in artifact schemas are informational summaries that point back to a `decision_log.yaml`
  entry. They do not constitute independent approval records and must not be used as gate-check
  evidence by the runtime (see `contracts/runtime_contract.md` Section 4).

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
