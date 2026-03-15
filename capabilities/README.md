# capabilities/

This directory contains **external tool integrations** that expose capabilities to agents during workflow execution.

## Relation to DevOS Architecture

The Capability System is one of the four DevOS systems. It provides agents with access to external tools without those tools having any knowledge of or dependency on the DevOS Kernel or workflow state.

Agents invoke capabilities through defined contracts. The Kernel is agnostic to all capability implementations. See `framework/contracts/capability_integration_contract.md` for the integration rules.

## Contents

| Directory | Purpose |
| --- | --- |
| `planning/` | Deterministic planning artifact management — parses and validates `project_plan.yaml` before workflow execution. See `capabilities/planning/README.md`. |
| `linear/` | Linear project sync adapter — projects validated planning artifacts into the Linear issue tracker |

## What Belongs Here

- Adapters for external services (git operations, CI runners, repository queries, external APIs)
- Tool clients with explicit input/output contracts
- Batch-oriented integrations that do not embed workflow or governance logic

Capability implementations must not contain workflow governance logic, agent reasoning, or domain rules.
