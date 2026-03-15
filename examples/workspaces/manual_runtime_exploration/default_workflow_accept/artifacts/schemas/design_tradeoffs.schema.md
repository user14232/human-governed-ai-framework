# Schema: `design_tradeoffs.md` (v1)

## Schema metadata

- **schema_id**: `design_tradeoffs`
- **version**: `v1`
- **artifact_name**: `design_tradeoffs.md`

## Responsibility

Capture explicit design options, assumptions, and trade-offs for a change.

## Owner roles

- `agent_planner`
- `agent_architecture_guardian` (addendum only)

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_implementer`
- `agent_reviewer`
- `agent_test_designer`

## Write policy

- **Mutability**: versioned (preferred) or append-only addendum
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version if this is a revision (null otherwise)

## Required sections (MUST appear in this order)

### 1) Context

- Change intent reference (`change_intent.yaml` id/ref)
- Plan reference (`implementation_plan.yaml` id/ref, if already created)

### 2) Options considered

List options. Each option must include:

- **id** (stable string)
- **description**
- **pros**
- **cons**
- **constraints** (references to `architecture_contract.md` and/or `domain_rules.md`)

### 3) Decision

- Selected option id
- Rationale (explicit)

### 4) Assumptions

Each assumption must include:

- **id**
- **statement**
- **risk if false**
- **how to validate**

### 5) Risks and mitigations

Each risk must include:

- **id**
- **risk**
- **mitigation**

### 6) Decision reference

- `decision_id` from `decision_log.yaml` that records the human approval for this artifact.
- Required when this artifact is subject to a `human_approval` gate in the workflow.
- Must match the `artifact_id` of this version of the artifact.

## Determinism requirements

- All assumptions must be explicit (no implicit behavior).
- Any change to decisions creates a new version or addendum with diffs described.
