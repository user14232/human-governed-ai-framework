# Schema: `arch_review_record.md` (v1)

## Schema metadata

- **schema_id**: `arch_review_record`
- **version**: `v1`
- **artifact_name**: `arch_review_record.md`

## Responsibility

Record the deterministic outcome of the `ARCH_CHECK` gate. This artifact is the required
evidence that architecture compliance was reviewed, regardless of whether a change was required.
It closes the governance gap at `ARCH_CHECK`: the workflow must not advance to `TEST_DESIGN`
without this artifact.

## Owner roles

- `agent_architecture_guardian`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_planner`
- `agent_implementer`
- `agent_reviewer`

## Write policy

- **Mutability**: versioned (new version if outcome changes after architecture proposal approval)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

These fields **must appear as the first lines of the file**, before any Markdown headings.
The runtime evaluates them as simple `key: value` lines (see `contracts/runtime_contract.md` Â§6.2 and Â§6.1).

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revised record (null otherwise)
- `outcome`: machine-readable gate signal â€” exactly one of:
  - `PASS` â€” the workflow may advance to `TEST_DESIGN`
  - `CHANGE_REQUIRED` â€” the workflow is blocked at `ARCH_CHECK`

**Syntax rule**: the `outcome` field must be expressed as a bare `key: value` line,
e.g. `outcome: PASS`. The runtime reads this field to evaluate the `arch_review_outcome`
condition in the workflow transition. A missing or misspelled value is treated as a gate failure.

## Required sections (MUST appear in this order)

### 1) Summary

- What was reviewed (references to `implementation_plan.yaml` id and `architecture_contract.md`
  version/ref).

### 2) Outcome

Human-readable elaboration of the machine-readable `outcome` field declared in the artifact header.
Must be consistent with the header field. Exactly one of:

- `PASS`: the planned changes comply with the architecture contract; no proposal required.
- `CHANGE_REQUIRED`: the planned changes require an explicit architecture change; see Section 4.

### 3) Findings

Each finding must include:

- **id**: stable string within this document
- **contract_section**: the exact section of `architecture_contract.md` referenced
- **assessment**: `compliant | violation | gap`
- **description**: explicit, non-interpretive description

If outcome is `PASS` and no issues were found, this section may contain a single entry
confirming compliance.

### 4) Architecture change reference (only if `CHANGE_REQUIRED`)

- `architecture_change_proposal_id`: the `id` of the produced `architecture_change_proposal.md`
- `required_decision_id`: the `decision_log.yaml` `decision_id` that must approve the proposal
  before the workflow may advance

When outcome is `CHANGE_REQUIRED`, the workflow is blocked at `ARCH_CHECK` until:

1. `architecture_change_proposal.md` is approved (explicit `decision_log.yaml` entry).
2. A new version of `arch_review_record.md` with `outcome: PASS` is produced.

## Determinism requirements

- The top-level `outcome` field must be one of `PASS` or `CHANGE_REQUIRED`; no other values permitted.
- The `outcome` field in Section 2 must match the top-level `outcome` field.
- Every finding must cite the exact contract section.
- No implicit pass: absence of findings does not constitute a `PASS`; the `outcome` field must
  be explicitly set to `PASS`.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added machine-readable outcome header field (PASS | CHANGE_REQUIRED) for deterministic gate evaluation (WF-05, AC-03). Updated Determinism requirements. |
