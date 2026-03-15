# DevOS Workspace Model

## Purpose of a Workspace

A DevOS workspace represents the state of a single DevOS project.  
It contains project-specific inputs, planning artifacts, and run history.

The workspace is separate from the DevOS runtime implementation.  
DevOS runtime components execute inside a workspace context, but runtime source code and framework definitions are maintained outside the workspace.

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

## Relationship to Examples

`examples/workspaces/` contains reference workspaces used for demonstration, simulation, and testing scenarios.

These examples illustrate expected workspace structure and artifact flow, and can be used as reproducible templates for new projects.
