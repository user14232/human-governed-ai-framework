id: DT-MANUAL-E2E-001
supersedes_id: null

## Context
- change_intent: CI-feature_feature_spec_artifact
- plan_ref: PLAN-MANUAL-E2E-001

## Options considered
- id: O-1
  description: Explicit feature_spec artifact before planning.
  pros: clear planning input contract.
  cons: one additional artifact to maintain.
  constraints: architecture_contract.md section-1

## Decision
- selected_option: O-1
- rationale: deterministic planning input takes precedence.

## Assumptions
- id: A-1
  statement: feature_spec schema is stable through this run.
  risk if false: downstream parsing breaks.
  how to validate: schema validation in planning stage.

## Risks and mitigations
- id: R-1
  risk: inconsistent artifact population
  mitigation: derive fields from explicit feature dictionary

## Decision reference
- decision_id: DEC-MANUAL-E2E-0001
