# Schema: `review_result.md` (v1)

## Schema metadata

- **schema_id**: `review_result`
- **version**: `v1`
- **artifact_name**: `review_result.md`

## Responsibility

Record a deterministic review outcome with traceable evidence references.

## Owner roles

- `agent_reviewer`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_release_manager`
- `agent_reflector`

## Write policy

- **Mutability**: versioned (new version per review pass)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

These fields **must appear as the first lines of the file**, before any Markdown headings.
The runtime evaluates them as simple `key: value` lines (see `contracts/runtime_contract.md` Â§6.2 and Â§6.1).

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a re-review pass (null otherwise)
- `outcome`: machine-readable gate signal â€” exactly one of:
  - `ACCEPTED` â€” the workflow may advance to `ACCEPTED`
  - `ACCEPTED_WITH_DEBT` â€” the workflow may advance to `ACCEPTED_WITH_DEBT` (requires human approval)
  - `FAILED` â€” the workflow transitions to `FAILED`

**Syntax rule**: the `outcome` field must be expressed as a bare `key: value` line,
e.g. `outcome: ACCEPTED`. The runtime reads this field to evaluate the `review_outcome`
condition in the workflow transition. A missing or misspelled value is treated as a gate failure.

## Required sections (MUST appear in this order)

### 1) Summary

- What was reviewed, at a high level (no new requirements).

### 2) Outcome

Human-readable elaboration of the machine-readable `outcome` field declared in the artifact header.
Must be consistent with the header field. One of:

- `ACCEPTED`
- `ACCEPTED_WITH_DEBT`
- `FAILED`

### 3) Evidence

Must reference:

- `implementation_plan.yaml` (id/ref)
- `test_report.json` (run_id/ref)
- relevant `architecture_contract.md` sections (if applicable)

### 4) Findings

Each finding must include:

- **id**: stable string within this document
- **type**: `issue | suggestion | note`
- **severity**: `blocker | major | minor`
- **traceability**:
  - plan item id(s) and/or contract section(s)
  - test failure reference(s) if relevant
- **description**: explicit, non-interpretive

### 5) Debt (only if `ACCEPTED_WITH_DEBT`)

Each debt item must include:

- owner
- follow-up suggestion
- explicit acceptance rationale

### 6) Decision reference

- `decision_id` from `decision_log.yaml` that records the human approval for this artifact.
- Required only when `outcome` is `ACCEPTED_WITH_DEBT` (this outcome requires human approval
  per the workflow gate).
- Must match the `artifact_id` of this version of `review_result.md`.
- Not required for `ACCEPTED` or `FAILED` outcomes.

## Determinism requirements

- The top-level `outcome` field must be one of `ACCEPTED`, `ACCEPTED_WITH_DEBT`, or `FAILED`.
- The `outcome` field in Section 2 must match the top-level `outcome` field.
- No unstated assumptions; all exceptions must be explicit.
- No outcome without referenced evidence.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added machine-readable outcome header field (ACCEPTED | ACCEPTED_WITH_DEBT | FAILED) for deterministic gate evaluation (WF-05, AC-03). Updated Determinism requirements. |
