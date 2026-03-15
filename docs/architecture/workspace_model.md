# DevOS Workspace Model

**Document type**: Architecture reference
**Status**: Normative for workspace layout
**Date**: 2026-03-15

---

## Purpose of a Workspace

A DevOS workspace represents the state of a single DevOS project.
It contains project-specific inputs, planning artifacts, and run history.

The workspace is separate from the DevOS runtime implementation.
DevOS runtime components execute inside a workspace context, but runtime source code and framework definitions are maintained outside the workspace.

A workspace is the **project boundary** for DevOS governance. All run artifacts, decisions, and events for a project live inside the workspace. The workspace is the unit of auditability.

## Typical Workspace Structure

Canonical workspace layout:

```text
workspace/
  inputs/
  planning/
  runs/
  .devos/
```

Directory purposes:

- `inputs/`: Domain inputs that define scope and constraints, such as `domain_scope.md` and `domain_rules.md`.
- `planning/`: Planning artifacts used to define and refine implementation intent.
- `runs/`: Execution history for workflow runs, including run-specific artifacts and evidence.
- `.devos/`: Internal DevOS runtime metadata used for local workspace state management.

## Relationship to DevOS Runtime

The DevOS runtime loads framework definitions from repository-level framework paths, including:

- `framework/workflows`
- `framework/artifacts/schemas`

Workspaces do not own framework definitions.  
They store project state and run outputs generated when the runtime executes against workspace inputs.

## Workspace Invariants

- The workspace is the only location where run state exists. There is no external database.
- All state is reconstructible from the workspace filesystem alone.
- The `runs/` directory is append-only from a run lifecycle perspective. Completed runs are not modified.
- The workspace does not own framework definitions. Framework files are loaded from the DevOS framework layer at runtime initialization.

## Relationship to the Four-Layer Architecture

The workspace sits at the boundary between the DevOS governance kernel and the external layers:

```
Planning Layer
    → produces change_intent.yaml → placed in workspace/planning/
         ↓
DevOS Governance Kernel
    → reads inputs/ and planning/ → writes to runs/<run_id>/
         ↓
Agent Execution Layer
    → reads from runs/<run_id>/artifacts/ → writes artifacts back to same location
         ↓
Engineering Tool Layer
    → called by agent adapters → output artifacts placed in runs/<run_id>/artifacts/
```

The workspace is the shared filesystem that all four layers interact with, but only the governance kernel manages workspace state transitions.

## Relationship to Examples

`examples/workspaces/` contains reference workspaces used for demonstration, simulation, and testing scenarios.

These examples illustrate expected workspace structure and artifact flow, and can be used as reproducible templates for new projects.
