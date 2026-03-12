# Schema: `architecture_change_proposal.md` (v1)

## Schema metadata

- **schema_id**: `architecture_change_proposal`
- **version**: `v1`
- **artifact_name**: `architecture_change_proposal.md`

## Responsibility

Propose an explicit change to the architecture contract. This is not an error; it is a governed change.

## Owner roles

- `agent_architecture_guardian`

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_planner`
- `agent_implementer`
- `agent_reviewer`

## Write policy

- **Mutability**: versioned
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revised proposal (null otherwise)

## Required sections (MUST appear in this order)

### 1) Summary

- One paragraph describing the proposed change.

### 2) Motivation (evidence)

- Cite the plan items and constraints that make this change necessary.

### 3) Proposed contract changes

- Exact changes to `architecture_contract.md` expressed as:
  - added rules
  - modified rules
  - removed rules

### 4) Impact analysis

- Affected layers/modules (conceptual, framework-agnostic)
- Risks and mitigations

### 5) Alternatives considered

- At least one alternative and why it was rejected.

### 6) Decision reference

- `decision_id` from `decision_log.yaml` that records the human decision (approve/reject/defer)
  for this proposal.
- Required before any implementation proceeds on architecture changes.
- Must match the `artifact_id` of this version of the proposal.

## Determinism requirements

- Proposed changes must be explicit and minimally scoped.
- No implicit architecture drift; implementation must not proceed without a recorded decision.
