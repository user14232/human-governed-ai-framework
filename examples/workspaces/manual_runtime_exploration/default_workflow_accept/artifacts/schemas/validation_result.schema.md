# Schema: `validation_result.md` (v1)

## Schema metadata

- **schema_id**: `validation_result`
- **version**: `v1`
- **artifact_name**: `validation_result.md`

## Responsibility

Record the deterministic outcome of a `domain_validation` capability invocation.
Validates a target artifact against project domain rules, scope, and glossary without
introducing new requirements or inferring unstated rules.

## Owner roles

- Project-provided `domain_validation` capability agent

## Allowed readers

- `human`
- `agent_orchestrator`
- `agent_planner`
- `agent_reviewer`
- `agent_architecture_guardian`

## Write policy

- **Mutability**: versioned (one result per validation invocation)
- **Overwrite allowed**: no

## Required artifact fields (top-level, before section content)

- `id`: stable instance identifier (see `contracts/runtime_contract.md` Section 3.2)
- `supersedes_id`: id of prior version (null if first validation of this artifact version)

## Required sections (MUST appear in this order)

### 1) Validation context

- Target artifact name and `artifact_id` validated
- Domain inputs consulted:
  - `domain_rules.md` (version/ref)
  - `domain_scope.md` (version/ref)
  - `glossary.md` (version/ref)
  - `source_policy.md` (version/ref)

### 2) Outcome

Exactly one of:

- `VALID`: target artifact complies with all consulted domain rules within checked scope
- `INVALID`: one or more violations found (see Section 3)
- `INCONCLUSIVE`: validation could not complete due to missing or ambiguous rule reference
  (each inconclusiveness must be documented with the specific gap)

### 3) Findings

Each finding must include:

- **id**: stable string within this document
- **rule_ref**: exact rule ID or section from `domain_rules.md` or `domain_scope.md`
- **finding_type**: `violation | out_of_scope | terminology_mismatch | inconclusive`
- **artifact_location**: section or field in the target artifact where the issue occurs
- **description**: explicit description referencing the cited rule

If outcome is `VALID` and no issues were found, include a single entry confirming compliance
with a reference to the checked rule set.

## Determinism requirements

- Every finding must cite an explicit rule ID or section; no implicit or inferred rules.
- Must not infer missing rules or expand scope beyond what is defined in domain inputs.
- Must not propose changes; only records compliance status.
