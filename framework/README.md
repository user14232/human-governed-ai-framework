# framework/

This directory contains the **normative governance definitions** loaded by the DevOS Kernel at runtime.

The framework is a specification layer — it defines rules and contracts that the kernel enforces. It contains no executable implementation code.

## Relation to DevOS Architecture

The framework is the **contract surface** between the DevOS Kernel and the rest of the system. The kernel reads workflow definitions, artifact schemas, agent role contracts, and system invariants from this directory. Nothing in this directory executes on its own.

See `docs/vision/devos_kernel_architecture.md` for the canonical architecture reference.

## Contents

| Directory | Purpose |
| --- | --- |
| `workflows/` | Workflow state machine definitions (`delivery_workflow.yaml`, `improvement_cycle.yaml`) |
| `artifacts/schemas/` | All artifact contracts — YAML schemas, JSON schemas, and markdown schema descriptions |
| `contracts/` | System invariants, runtime contract, capability integration contract, versioning policy, migration contract |
| `agents/` | Agent role contracts — one file per role defining responsibilities, inputs, outputs, and prohibitions |

## What Belongs Here

- Workflow YAML definitions (state machines, transitions, gate conditions)
- Artifact schema files (`.schema.yaml`, `.schema.json`, `.schema.md`)
- Agent role contract documents (`.md` files describing a single agent role)
- System-level contracts and invariants

Do not place runtime implementation code, project-specific domain rules, or run artifacts here.
