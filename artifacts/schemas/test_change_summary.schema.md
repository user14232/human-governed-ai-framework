# Schema: `test_change_summary.md` (v1)

## Schema metadata

- **schema_id**: `test_change_summary`
- **version**: `v1`
- **artifact_name**: `test_change_summary.md`

## Responsibility

Record an auditable summary of test code changes mapped to `test_design.yaml`.

## Owner roles

- `agent_test_author`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_test_runner`
- `agent_reviewer`

## Write policy

- **Mutability**: versioned (new version per change pass)
- **Overwrite allowed**: no

## Required sections (MUST appear in this order)

### 1) Summary

- What tests were added/changed (no speculative scope).

### 2) Files touched

- Ordered list of test file paths touched.

### 3) Mapping to test cases

- For each touched file, list test case IDs from `test_design.yaml`.

### 4) Deviations (if any)

- Explicit rationale; requires new `test_design.yaml` + human approval if design changed.

## Determinism requirements

- Traceability to `test_design.yaml` test case IDs is mandatory.
