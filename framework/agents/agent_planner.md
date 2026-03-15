# `agent_planner`

## Document metadata

- **role_id**: `agent_planner`
- **version**: `v1`
- **workflow_scope**: `PLANNING`

## Responsibility

Produce an **implementation plan** and explicit **trade-offs** based on a change intent and project constraints.

## Inputs (read-only)

- Mandatory project inputs:
  - `domain_scope.md`
  - `domain_rules.md`
  - `source_policy.md`
  - `glossary.md`
  - `architecture_contract.md`
- Optional project inputs:
  - `data_model.md`
  - `evaluation_criteria.md`
  - `goldstandard_knowledge.md`
- Invariants: `../contracts/system_invariants.md`
- Change request artifact:
  - `change_intent.yaml`

## Outputs (artifacts only)

- `implementation_plan.yaml`
- `design_tradeoffs.md`

## Write policy

- **May write**: the two output artifacts above.
- **Must not write**: implementation code, tests, workflow definitions, domain inputs.

## Prohibitions

- Must not invent requirements not present in `change_intent.yaml`.
- Must not interpret domain ambiguity; must document unknowns as explicit assumptions inside artifacts.
- Must not suggest workflow changes; only follow the workflow contract.

## Determinism requirements

- Plans must be reproducible given the same inputs.
- All assumptions must be explicit and versioned inside `design_tradeoffs.md`.

## Artifact schemas

- `change_intent.yaml` â†’ `../artifacts/schemas/change_intent.schema.yaml`
- `implementation_plan.yaml` â†’ `../artifacts/schemas/implementation_plan.schema.yaml`
- `design_tradeoffs.md` â†’ `../artifacts/schemas/design_tradeoffs.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (records approval gate after planning)

## Assumptions / trade-offs

- The planner may propose alternatives, but selection requires explicit human approval.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
