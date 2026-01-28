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

### 6) Human approvals

- Approver identifier(s)
- ISO-8601 timestamp(s)

## Determinism requirements

- All assumptions must be explicit (no implicit behavior).
- Any change to decisions creates a new version or addendum with diffs described.
