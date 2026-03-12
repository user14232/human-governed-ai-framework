# Agents (role contracts) â€” v1

## Responsibility

This folder contains **role contracts** for framework agents.
Each agent is a **single-shot role** with explicit inputs/outputs and prohibitions.

## Contract shape (applies to all agents)

Each agent contract MUST define:

- **Responsibility** (single responsibility)
- **Inputs** (artifacts and read-only reference docs)
- **Outputs** (artifacts only)
- **Write policy** (what it may write, what it must never write)
- **Prohibitions** (explicit â€œmust notâ€)
- **Determinism requirements**

## v1 Core roles (fully integrated into delivery workflow)

- `agent_orchestrator`
- `agent_planner`
- `agent_architecture_guardian`
- `agent_test_designer`
- `agent_test_author`
- `agent_test_runner`
- `agent_branch_manager`
- `agent_implementer`
- `agent_reviewer`

## v1 Improvement cycle roles

- `agent_reflector`
- `agent_improvement_designer`

## v1.1 roles (defined, release workflow deferred)

- `agent_release_manager` â€” defined and ready; release is not a workflow state in v1.
  Use post-acceptance at project discretion.

## System actor (meta-role)

This is not an autonomous agent; it is an explicit workflow actor for auditability:

- `human_decision_authority`

## Invariants reference

See: `../contracts/system_invariants.md`  
See: `../contracts/runtime_contract.md`
