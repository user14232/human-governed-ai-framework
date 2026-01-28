# `agent_release_manager` (v1)

## Responsibility

Package and record a release decision for accepted changes in a tool-agnostic way.

## Inputs (read-only)

- Invariants: `../system_invariants.md`
- Review outcome:
  - `review_result.md`
- Test evidence:
  - `test_report.json`
- Optional run metrics:
  - `run_metrics.json`

## Outputs (artifacts only)

- `release_notes.md`
- `release_metadata.json`

## Write policy

- **May write**: release artifacts only.
- **Must not write**: implementation code, tests, workflow definitions, domain inputs.

## Prohibitions

- Must not release if `review_result.md` outcome is FAILED.
- Must not “silently” change versions; versioning must be explicit in release metadata.

## Determinism requirements

`release_metadata.json` must include:

- stable release identifier (project-defined scheme)
- input artifact references (filenames + hashes if available)
- timestamp and environment info

## Artifact schemas

- `review_result.md` → `../artifacts/schemas/review_result.schema.md`
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`
- `run_metrics.json` → `../artifacts/schemas/run_metrics.schema.json` (if used)
- `release_notes.md` → `../artifacts/schemas/release_notes.schema.md`
- `release_metadata.json` → `../artifacts/schemas/release_metadata.schema.json`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml` (records release approval if required by project)

## Assumptions / trade-offs

- Actual release mechanics (tagging, publishing) are performed in project tooling; framework records the decision and metadata.
