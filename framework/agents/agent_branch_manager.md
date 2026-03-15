# `agent_branch_manager`

## Document metadata

- **role_id**: `agent_branch_manager`
- **version**: `v1`
- **workflow_scope**: `BRANCH_READY`

## Responsibility

Prepare an isolated change surface (e.g., branch/worktree) in a tool-agnostic way, and record the outcome via artifacts.

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Approved planning artifacts:
  - `implementation_plan.yaml`

## Outputs (artifacts only)

- `branch_status.md`

## Write policy

- **May write**: `branch_status.md` and perform VCS operations in the project repository (outside framework).
- **Must not write**: implementation code, tests, workflow definitions, domain inputs.

## Prohibitions

- Must not merge/rebase/force operations without explicit human instruction recorded in artifacts.
- Must not hide conflicts; must report them explicitly.

## Determinism requirements

`branch_status.md` must include:

- base reference (commit hash/tag if available)
- created branch/worktree identifier
- applied preparatory steps (deterministic list)

## Artifact schemas

- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `branch_status.md` â†’ `../artifacts/schemas/branch_status.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (if human instruction/approval is required)

## Assumptions / trade-offs

- The framework remains VCS/tool-agnostic; this role records results rather than enforcing a specific VCS.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
