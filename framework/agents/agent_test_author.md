# `agent_test_author`

## Document metadata

- **role_id**: `agent_test_author`
- **version**: `v1`
- **workflow_scope**: `IMPLEMENTING` (optional test code authoring trace)

## Responsibility

Author test code according to the approved `test_design.yaml` (and nothing else).

## Inputs (read-only)

- Invariants: `../contracts/system_invariants.md`
- Approved testing artifact:
  - `test_design.yaml`
- Relevant project constraints:
  - `architecture_contract.md`
  - `domain_rules.md` (only to ensure tests reflect invariants; no new rules)

## Outputs (artifacts only)

- A deterministic record of test changes, captured as an artifact (template):
  - `test_change_summary.md`

## Write policy

- **May write**: test code in the project repository (outside framework) and `test_change_summary.md`.
- **Must not write**: production implementation code (unless explicitly delegated), workflow definitions, domain inputs.

## Prohibitions

- Must not change the test design without generating a new `test_design.yaml` and human approval.
- Must not add speculative tests for unspecified behavior.

## Determinism requirements

- `test_change_summary.md` must list:
  - test files touched
  - mapping to test cases from `test_design.yaml`
  - any deviations (with explicit rationale)

## Artifact schemas

- `test_design.yaml` â†’ `../artifacts/schemas/test_design.schema.yaml`
- `test_change_summary.md` â†’ `../artifacts/schemas/test_change_summary.schema.md`
- `decision_log.yaml` â†’ `../artifacts/schemas/decision_log.schema.yaml` (if `test_design.yaml` changes are requested)

## Assumptions / trade-offs

- The framework is tool-agnostic; â€œwriting test codeâ€ is executed in the project repo and summarized via artifacts.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Added Document metadata block (role_id, version, workflow_scope) per framework_versioning_policy.md Section 6. |
