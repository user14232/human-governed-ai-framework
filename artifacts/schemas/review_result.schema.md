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

## Required sections (MUST appear in this order)

### 1) Summary

- What was reviewed, at a high level (no new requirements).

### 2) Outcome

One of:

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

### 6) Decision record

- Who approved (human identifier)
- When (ISO-8601)

## Determinism requirements

- No unstated assumptions; all exceptions must be explicit.
- No outcome without referenced evidence.
