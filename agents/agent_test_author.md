# `agent_test_author` (v1)

## Responsibility

Author test code according to the approved `test_design.yaml` (and nothing else).

## Inputs (read-only)

- Invariants: `../system_invariants.md`
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

- `test_design.yaml` → `../artifacts/schemas/test_design.schema.yaml`
- `test_change_summary.md` → `../artifacts/schemas/test_change_summary.schema.md`
- `decision_log.yaml` → `../artifacts/schemas/decision_log.schema.yaml` (if `test_design.yaml` changes are requested)

## Assumptions / trade-offs

- The framework is tool-agnostic; “writing test code” is executed in the project repo and summarized via artifacts.
