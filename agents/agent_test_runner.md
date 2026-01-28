# `agent_test_runner` (v1)

## Responsibility

Execute the test suite deterministically and publish an auditable test report artifact.

## Inputs (read-only)

- Invariants: `../system_invariants.md`
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

- Must not “massage” results (no filtering of failures).
- Must not re-run selectively unless explicitly recorded (reproducible rerun policy).

## Determinism requirements

`test_report.json` must include:

- stable run identifier
- environment summary (tool versions, OS, deterministic flags if any)
- executed test selection definition
- pass/fail counts and failure details

## Artifact schemas

- `test_design.yaml` → `../artifacts/schemas/test_design.schema.yaml`
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`
- `run_metrics.json` → `../artifacts/schemas/run_metrics.schema.json` (if used)

## Assumptions / trade-offs

- Full reproducibility depends on project execution environment; the framework records what was run and where.
