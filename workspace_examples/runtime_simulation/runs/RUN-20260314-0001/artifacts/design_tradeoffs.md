id: DT-001
supersedes_id: null

## Context
- change_intent: CI-EXAMPLE-001
- plan_ref: PLAN-001

## Options considered
- id: O-1
  description: Human-as-agent deterministic invocation.
  pros: reproducible events.
  cons: no real model execution.
  constraints: architecture_contract.md section-1

## Decision
- selected_option: O-1
- rationale: deterministic replay first.

## Assumptions
- id: A-1
  statement: Artifact schemas remain stable during run.
  risk if false: gate failures.
  how to validate: schema load before invocation.

## Risks and mitigations
- id: R-1
  risk: missing schema file
  mitigation: copy full schemas into workspace

## Decision reference
- decision_id: DEC-0001
