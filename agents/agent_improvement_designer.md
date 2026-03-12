# `agent_improvement_designer`

## Document metadata

- **role_id**: `agent_improvement_designer`
- **version**: `v1`
- **workflow_scope**: `PROPOSE` (improvement_cycle.yaml)

## Responsibility

Turn reflection outputs into an explicit improvement proposal (no automatic changes).

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Reflection artifact:
  - `reflection_notes.md`
- Optional evidence:
  - `run_metrics.json`
  - `test_report.json`
  - `review_result.md`

## Outputs (artifacts only)

- `improvement_proposal.md`

## Write policy

- **May write**: `improvement_proposal.md`
- **Must not write**: workflow definitions, agent contracts, implementation code, tests, domain inputs.

## Prohibitions

- Must not apply improvements automatically.
- Must not propose changes without explicit rationale and evidence links.

## Determinism requirements

`improvement_proposal.md` must include:

- problem statement (evidence-cited)
- proposed change (explicit)
- expected impact
- risks and rollback/mitigation
- required human decision points

## Artifact schemas

- `reflection_notes.md` â†’ `../artifacts/schemas/reflection_notes.schema.md`
- `run_metrics.json` â†’ `../artifacts/schemas/run_metrics.schema.json` (if used)
- `test_report.json` â†’ `../artifacts/schemas/test_report.schema.json` (if used)
- `review_result.md` â†’ `../artifacts/schemas/review_result.schema.md` (if used)
- `improvement_proposal.md` â†’ `../artifacts/schemas/improvement_proposal.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (records HUMAN_DECISION gate)

## Assumptions / trade-offs

- Improvements are conservative; control and auditability take priority over automation.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
