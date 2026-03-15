# `implementer`

## Document metadata

- **role_id**: `implementer`
- **version**: `v1`
- **workflow_scope**: `IMPLEMENTING`

## Responsibility

Implement the approved plan in the project codebase. Produce an auditable implementation summary.

The implementer must not deviate from the approved plan without an explicit architecture change proposal. Scope is fixed to what is described in `implementation_plan.yaml`.

## Inputs

- `implementation_plan.yaml`
- `design_tradeoffs.md`
- `arch_review_record.md`
- `architecture_contract.md`
- `test_design.yaml` (if available)

## Outputs

- `implementation_summary.md`

## Write policy

- **May write**: implementation code in the project repository (outside framework) and `implementation_summary.md`.
- **Must not write**: workflow definitions, domain input artifacts, architecture contract text (except via proposal).

## Prohibitions

- Must not change architecture rules implicitly; must produce `architecture_change_proposal.md` if a deviation is required.
- Must not broaden scope beyond `change_intent.yaml` and `implementation_plan.yaml`.
- May call capabilities (git, filesystem, build tools) but must not invoke reasoning roles.

## Determinism requirements

`implementation_summary.md` must include:

- list of files changed (paths)
- mapping from changes to plan items (IDs)
- any deviations and the explicit reason

## Artifact schemas

- `implementation_plan.yaml` → `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` → `../artifacts/schemas/design_tradeoffs.schema.md`
- `arch_review_record.md` → `../artifacts/schemas/arch_review_record.schema.md`
- `implementation_summary.md` → `../artifacts/schemas/implementation_summary.schema.md`
- `architecture_change_proposal.md` → `../artifacts/schemas/architecture_change_proposal.schema.md` (if deviation required)

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-15 | Consolidated from agent_implementer.md; role_id simplified per four-role model. |
