# Agents (role contracts) — v1

## Responsibility

This folder contains **role contracts** for framework agents.
Each agent is a **single-shot role** with explicit inputs/outputs and prohibitions.

## Contract shape (applies to all agents)

Each agent contract MUST define:

- **Responsibility** (single responsibility)
- **Inputs** (artifacts and read-only reference docs)
- **Outputs** (artifacts only)
- **Write policy** (what it may write, what it must never write)
- **Prohibitions** (explicit “must not”)
- **Determinism requirements**

## Core roles

- `agent_orchestrator`
- `agent_planner`
- `agent_architecture_guardian`
- `agent_test_designer`
- `agent_test_author`
- `agent_test_runner`
- `agent_branch_manager`
- `agent_implementer`
- `agent_reviewer`
- `agent_release_manager`

## Improvement cycle roles

- `agent_reflector`
- `agent_improvement_designer`

## System actor (meta-role)

This is not an autonomous agent; it is an explicit workflow actor for auditability:

- `human_decision_authority`

## Invariants reference

See: `../system_invariants.md`
