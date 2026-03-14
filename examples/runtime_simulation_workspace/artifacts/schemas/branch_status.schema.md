# Schema: `branch_status.md` (v1)

## Schema metadata

- **schema_id**: `branch_status`
- **version**: `v1`
- **artifact_name**: `branch_status.md`

## Responsibility

Record the deterministic outcome of preparing an isolated change surface (branch/worktree/etc.).

## Owner roles

- `agent_branch_manager`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_implementer`
- `agent_reviewer`

## Write policy

- **Mutability**: versioned (new version per attempt)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revised record (null otherwise)

## Required sections (MUST appear in this order)

### 1) Summary

- What was prepared (tool-agnostic).

### 2) Base reference

- Base identifier (commit hash/tag if available; otherwise explicit string).

### 3) Change surface identifier

- Branch/worktree identifier created or selected.

### 4) Steps performed

- Deterministic list of steps (ordered).

### 5) Issues / conflicts (if any)

- Explicit list; no hidden conflicts.

### 6) Decision record (if applicable)

- `decision_id` reference in `decision_log.yaml` if any human instruction was required.

## Determinism requirements

- Stable identifiers where available.
- No implied â€œsuccessâ€; explicit outcome must be stated.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added id and supersedes_id to Required artifact fields for versioning consistency (AC-02). |
