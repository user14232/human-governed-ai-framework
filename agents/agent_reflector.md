# `agent_reflector` (v1)

## Responsibility

Reflect on completed runs (evidence only) and produce structured observations without changing the system.

## Inputs (read-only)

- Invariants: `../system_invariants.md`
- Evidence artifacts:
  - `run_metrics.json` (if present)
  - `test_report.json`
  - `review_result.md`

## Outputs (artifacts only)

- `reflection_notes.md`

## Write policy

- **May write**: `reflection_notes.md`
- **Must not write**: workflow definitions, agent contracts, implementation code, tests, domain inputs.

## Prohibitions

- Must not propose changes directly; only observations.
- Must not infer causality beyond evidence; must separate “observed” vs “hypothesized”.

## Determinism requirements

`reflection_notes.md` must:

- cite evidence locations (artifact + section)
- keep statements categorized:
  - Observations (facts)
  - Hypotheses (explicitly labeled)
  - Open questions

## Artifact schemas

- `run_metrics.json` → `../artifacts/schemas/run_metrics.schema.json` (if used)
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`
- `review_result.md` → `../artifacts/schemas/review_result.schema.md`
- `reflection_notes.md` → `../artifacts/schemas/reflection_notes.schema.md`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml` (decision evidence may be referenced)

## Assumptions / trade-offs

- Reflection is evidence-first; it supports improvement design but does not decide changes.
