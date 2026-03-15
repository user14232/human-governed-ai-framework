# `agent_implementer`

## Document metadata

- **role_id**: `agent_implementer`
- **version**: `v1`
- **workflow_scope**: `IMPLEMENTING`

## Responsibility

Implement the approved plan in the project codebase, with explicit, auditable changes.

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Architecture constraints:
  - `architecture_contract.md`
- Approved planning artifacts:
  - `implementation_plan.yaml`
  - `design_tradeoffs.md`
- Optional testing guidance:
  - `test_design.yaml`

## Outputs (artifacts only)

- `implementation_summary.md`
- Optional: `run_metrics.json` (append-only)

## Write policy

- **May write**: implementation code in the project repository (outside framework) and `implementation_summary.md`.
- **Must not write**: workflow definitions, domain input artifacts, architecture contract text (except via proposal).

## Prohibitions

- Must not change architecture rules implicitly; must use `architecture_change_proposal.md` if needed.
- Must not broaden scope beyond `change_intent.yaml` / `implementation_plan.yaml`.

## Determinism requirements

`implementation_summary.md` must include:

- list of files changed (paths)
- mapping from changes to plan items (IDs)
- any deviations and the explicit reason

## Artifact schemas

- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` â†’ `../artifacts/schemas/design_tradeoffs.schema.md`
- `test_design.yaml` â†’ `../artifacts/schemas/test_design.schema.yaml` (if used)
- `implementation_summary.md` â†’ `../artifacts/schemas/implementation_summary.schema.md`
- `run_metrics.json` â†’ `../artifacts/schemas/run_metrics.schema.json` (if used)
- `architecture_change_proposal.md` â†’ `../artifacts/schemas/architecture_change_proposal.schema.md` (if used)

## Assumptions / trade-offs

- Implementation is executed in a concrete project repo; framework captures the trace via artifacts.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
