# `agent_branch_manager` (v1)

## Responsibility

Prepare an isolated change surface (e.g., branch/worktree) in a tool-agnostic way, and record the outcome via artifacts.

## Inputs (read-only)

- Invariants: `../system_invariants.md`
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

- `implementation_plan.yaml` → `../artifacts/schemas/implementation_plan.schema.yaml`
- `branch_status.md` → `../artifacts/schemas/branch_status.schema.md`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml` (if human instruction/approval is required)

## Assumptions / trade-offs

- The framework remains VCS/tool-agnostic; this role records results rather than enforcing a specific VCS.
