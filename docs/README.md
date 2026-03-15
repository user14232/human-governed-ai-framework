# DevOS Documentation Map

This documentation set is organized to make system intent, architecture, and execution behavior easy to find.

## DevOS System Layers

- **Framework**: The stable specification layer that defines workflows, artifacts, contracts, and expected behavior.
- **Runtime**: The execution layer that loads workflows, evaluates gates, invokes agents, persists artifacts, and records run state.
- **Workspace**: The project state layer where domain inputs, planning context, and historical run outputs are stored.
- **Integrations**: Adapter layer that connects DevOS to external systems (for example planning providers and project systems).

## Documentation Directories

- `docs/architecture`: High-level architecture, layering, and system design references.
- `docs/framework`: Core framework concepts such as event model, workflow model, and knowledge/query contracts.
- `docs/runtime`: Runtime engine behavior, execution flow, and runtime module architecture.
- `docs/governance`: Boundaries, non-goals, anti-patterns, and project guardrails.
- `docs/integrations`: Integration-specific architecture and adapter documentation.
- `docs/future`: Future-facing design ideas and possible roadmap directions.
- `docs/archive`: Historical plans, readiness notes, and implementation records retained for traceability.

## Recommended Reading Order for New Contributors

1. `docs/architecture/DEV_OS_product_vision.md`
2. `docs/architecture/devos_architecture.md`
3. `docs/framework/event_model.md`
4. `docs/framework/workflow_state_machine.md`
5. `docs/runtime/runtime_module_architecture.md`

After these, read module-specific documents in `docs/framework` and `docs/runtime`, then consult `docs/governance` for constraints and non-goals.

## Repository-to-Documentation Mapping

Documentation mirrors repository structure so that conceptual and implementation views stay aligned:

- `framework/` -> specification and contract definitions
- `runtime/` -> workflow execution engine and run-time orchestration
- `integrations/` -> external system adapters and provider implementations
- `examples/` -> example workspaces, sample inputs, and reproducible references

When searching for details, start with the corresponding `docs/*` section, then open the matching repository directory for implementation context.
