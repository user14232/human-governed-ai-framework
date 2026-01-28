# Schema: `improvement_proposal.md` (v1)

## Schema metadata

- **schema_id**: `improvement_proposal`
- **version**: `v1`
- **artifact_name**: `improvement_proposal.md`

## Responsibility

Propose a controlled improvement to the framework usage or process, without applying it automatically.

## Owner roles

- `agent_improvement_designer`

## Allowed readers

- `human`
- `agent_orchestrator`

## Write policy

- **Mutability**: versioned
- **Overwrite allowed**: no

## Required sections

### 1) Problem statement (evidence-cited)

- Cite `reflection_notes.md` and relevant evidence artifacts.

### 2) Proposed change

- Explicitly describe what would change.

### 3) Expected impact

- Benefits, costs, and any workflow/contract implications.

### 4) Risks and mitigations

- Include rollback/containment plan.

### 5) Required human decisions

- List the exact approvals needed.

### 6) Decision record

- Approved? (yes/no)
- Approver identifier(s)
- ISO-8601 timestamp(s)

## Determinism requirements

- No “implicit adoption”: proposal must not modify any file by itself.
- All claims must be evidence-linked or explicitly labeled as hypotheses.
