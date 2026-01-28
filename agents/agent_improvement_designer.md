# `agent_improvement_designer` (v1)

## Responsibility

Turn reflection outputs into an explicit improvement proposal (no automatic changes).

## Inputs (read-only)

- Invariants: `../system_invariants.md`
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

- `reflection_notes.md` → `../artifacts/schemas/reflection_notes.schema.md`
- `run_metrics.json` → `../artifacts/schemas/run_metrics.schema.json` (if used)
- `test_report.json` → `../artifacts/schemas/test_report.schema.json` (if used)
- `review_result.md` → `../artifacts/schemas/review_result.schema.md` (if used)
- `improvement_proposal.md` → `../artifacts/schemas/improvement_proposal.schema.md`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml` (records HUMAN_DECISION gate)

## Assumptions / trade-offs

- Improvements are conservative; control and auditability take priority over automation.
