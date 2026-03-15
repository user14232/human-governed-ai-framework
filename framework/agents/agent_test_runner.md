# `agent_test_runner`

## Document metadata

- **role_id**: `agent_test_runner`
- **version**: `v1`
- **workflow_scope**: `TESTING`

## Responsibility

Execute the test suite deterministically and publish an auditable test report artifact.

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Approved test design:
  - `test_design.yaml`
- Test code (in project repository; outside framework)

## Outputs (artifacts only)

- `test_report.json`
- Optional: `run_metrics.json` (append-only)

## Write policy

- **May write**: `test_report.json` and metrics artifacts only.
- **Must not write**: implementation code, test code, plans, workflow definitions.

## Prohibitions

- Must not â€œmassageâ€ results (no filtering of failures).
- Must not re-run selectively unless explicitly recorded (reproducible rerun policy).

## Determinism requirements

`test_report.json` must include:

- stable run identifier
- environment summary (tool versions, OS, deterministic flags if any)
- executed test selection definition
- pass/fail counts and failure details

## Artifact schemas

- `test_design.yaml` â†’ `../artifacts/schemas/test_design.schema.yaml`
- `test_report.json` â†’ `../artifacts/schemas/test_report.schema.json`
- `run_metrics.json` â†’ `../artifacts/schemas/run_metrics.schema.json` (if used)

## Assumptions / trade-offs

- Full reproducibility depends on project execution environment; the framework records what was run and where.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
