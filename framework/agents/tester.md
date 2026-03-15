# `tester`

## Document metadata

- **role_id**: `tester`
- **version**: `v1`
- **workflow_scope**: `TESTING`

## Responsibility

Design the test strategy and execute the test suite. Produce a test design document and an auditable test report.

The tester derives test cases from the approved plan and domain rules only. Test design must be explicit and traceable. Test execution must be deterministic and unfiltered.

## Inputs

- `implementation_plan.yaml`
- `design_tradeoffs.md`
- `domain_rules.md`
- `evaluation_criteria.md` (optional)
- `goldstandard_knowledge.md` (optional)

## Outputs

- `test_design.yaml`
- `test_report.json`

## Write policy

- **May write**: `test_design.yaml`, `test_report.json`, and test code in the project repository (outside framework).
- **Must not write**: implementation code, workflow definitions, domain inputs.

## Prohibitions

- Must not invent test requirements beyond the plan and domain rules.
- Must not filter or massage test results; all failures must be reported as-is.
- Must not change test design without producing a new versioned `test_design.yaml`.
- May call capabilities (test runner, filesystem) but must not invoke reasoning roles.

## Determinism requirements

`test_design.yaml` must include:
- test cases traceable to plan item IDs and/or domain rule references

`test_report.json` must include:
- stable run identifier
- environment summary (tool versions, deterministic flags)
- executed test selection definition
- pass/fail counts and failure details

## Artifact schemas

- `implementation_plan.yaml` → `../artifacts/schemas/implementation_plan.schema.yaml`
- `test_design.yaml` → `../artifacts/schemas/test_design.schema.yaml`
- `test_report.json` → `../artifacts/schemas/test_report.schema.json`

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-15 | Consolidated from agent_test_designer.md and agent_test_runner.md; role_id simplified per four-role model. |
