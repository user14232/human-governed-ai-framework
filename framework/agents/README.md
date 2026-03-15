# Agents (role contracts) - v1.1

## Responsibility

This folder defines deterministic role contracts for DevOS agents. Each role is single-shot,
artifact-driven, and bound by explicit write boundaries and prohibitions.

## Contract Shape (required fields)

Every agent contract must define:

- responsibility (single purpose)
- inputs (artifacts and read-only references)
- outputs (artifacts only)
- write policy (what may be written and what is forbidden)
- prohibitions (explicit must-not rules)
- determinism requirements

## Delivery Workflow Roles

Integrated into the primary delivery state machine:

- `agent_orchestrator`
- `agent_planner`
- `agent_architecture_guardian`
- `agent_test_designer`
- `agent_test_author`
- `agent_test_runner`
- `agent_branch_manager`
- `agent_implementer`
- `agent_reviewer`

## Improvement Cycle Roles

Asynchronous improvement loop support:

- `agent_reflector`
- `agent_improvement_designer`

## Pre-Workflow Authoring Roles

These roles run before delivery workflow execution and produce planning artifacts:

- `agent_work_item_author` - authors `.devOS/planning/project_plan.yaml` from a human brief,
  aligned with `devos/planning/contracts/work_item_contract.md` and linter rules.

## Release Role

- `agent_release_manager` - defined role for post-acceptance release activities.

## System Actor

- `human_decision_authority` (explicit governance actor, not autonomous)

## References

- `../contracts/system_invariants.md`
- `../contracts/runtime_contract.md`
