# `agent_reflector`

## Document metadata

- **role_id**: `agent_reflector`
- **version**: `v1`
- **workflow_scope**: `REFLECT` (improvement_cycle.yaml); optional post-run knowledge extraction

## Responsibility

Reflect on completed runs (evidence only) and produce structured observations without changing the system.

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Evidence artifacts:
  - `run_metrics.json` (**required** when operating in the improvement cycle; the workflow
    transition `OBSERVE â†’ REFLECT` requires this artifact â€” see `improvement_cycle.yaml`)
  - `test_report.json`
  - `review_result.md`

## Outputs (artifacts only)

- `reflection_notes.md`

## Write policy

- **May write**: `reflection_notes.md`
- **Must not write**: workflow definitions, agent contracts, implementation code, tests, domain inputs.

## Prohibitions

- Must not propose changes directly; only observations.
- Must not infer causality beyond evidence; must separate â€œobservedâ€ vs â€œhypothesizedâ€.

## Determinism requirements

`reflection_notes.md` must:

- cite evidence locations (artifact + section)
- keep statements categorized:
  - Observations (facts)
  - Hypotheses (explicitly labeled)
  - Open questions

## Artifact schemas

- `run_metrics.json` â†’ `../artifacts/schemas/run_metrics.schema.json` (required in improvement cycle context)
- `test_report.json` â†’ `../artifacts/schemas/test_report.schema.json`
- `review_result.md` â†’ `../artifacts/schemas/review_result.schema.md`
- `reflection_notes.md` â†’ `../artifacts/schemas/reflection_notes.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (decision evidence may be referenced)

## Assumptions / trade-offs

- Reflection is evidence-first; it supports improvement design but does not decide changes.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
