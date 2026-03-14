# Schema: `implementation_summary.md` (v1)

## Schema metadata

- **schema_id**: `implementation_summary`
- **version**: `v1`
- **artifact_name**: `implementation_summary.md`

## Responsibility

Provide an auditable, deterministic trace of implementation changes mapped to the approved plan.

## Owner roles

- `agent_implementer`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_reviewer`
- `agent_test_designer`

## Write policy

- **Mutability**: versioned (new version per implementation pass)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revised record (null otherwise)

## Required sections (MUST appear in this order)

### 1) Summary

- High-level description of what was implemented (no new requirements).

### 2) Inputs

- References to:
  - `implementation_plan.yaml` (id/ref)
  - `design_tradeoffs.md` (version/ref)

### 3) Files changed

- Ordered list of file paths changed.

### 4) Plan mapping

- Map each changed area to plan item IDs.

### 5) Deviations (if any)

- Each deviation must include:
  - plan item id(s) affected
  - explicit reason
  - risk/impact notes

### 6) Follow-ups (optional)

- Only if explicitly in scope.

## Determinism requirements

- No unstated assumptions.
- Plan item IDs must be cited for all changes.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added id and supersedes_id to Required artifact fields for versioning consistency (AC-02). |
