# Schema: `release_notes.md` (v1)

## Schema metadata

- **schema_id**: `release_notes`
- **version**: `v1`
- **artifact_name**: `release_notes.md`

## Responsibility

Human-readable summary of an approved release, derived from review and test evidence.

## Owner roles

- `agent_release_manager`

## Allowed readers

- `human`
- all_framework_roles: true

## Write policy

- **Mutability**: versioned
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revised record (null otherwise)

## Required sections

### Release summary

- What is released (no new requirements).

### Evidence

- Reference `review_result.md` (outcome must not be FAILED)
- Reference `test_report.json`

### Changes included

- Bullet list of included scope items (map to plan item IDs where possible)

### Known issues / debt

- Include only what was accepted as debt in `review_result.md`

## Determinism requirements

- Must not introduce new claims beyond referenced evidence.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added id and supersedes_id to Required artifact fields for versioning consistency (AC-02). |
