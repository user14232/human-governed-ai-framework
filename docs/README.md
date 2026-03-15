# DevOS Documentation Map

This documentation set is organized around the DevOS **workflow governance kernel** and its relationship to external planning, agent, and tooling systems.

## Documentation Model

```
Vision and positioning
    What DevOS is, its architectural position, and long-term direction.

Architecture references
    Detailed specifications for integration, agent contracts, LLM strategy,
    and the full development pipeline.

MVP Runtime (active code)
    The execution engine that implements run lifecycle, workflow transitions,
    gate validation, artifact handling, decision reading, and event emission.

Framework Definitions (contracts and schemas)
    The normative specification layer that defines workflows, artifacts,
    agent contracts, and system invariants. Consumed by the runtime.

Future Features / Roadmap (parked ideas)
    Post-MVP capabilities documented and preserved but not part of the
    current runtime implementation.
```

## DevOS Systems

DevOS consists of four systems. See `docs/vision/devos_kernel_architecture.md` for the canonical description.

- **DevOS Kernel**: The governance core — run lifecycle, workflow transitions, gate evaluation, artifact validation, decision logging, event tracking. All orchestration and system control is deterministic runtime logic. No AI reasoning.
- **Agent Runtime**: External agents implement DevOS contracts and produce all workflow artifacts. Agents are used only for cognitive tasks (reasoning, synthesis, generation). The Kernel invokes them through the `AgentAdapter` protocol.
- **Capability System**: Tool integrations available to agents — Git, Pytest, Ruff, Linear, MCP servers. The Kernel is agnostic to all capability implementations.
- **Knowledge System**: Persistent engineering memory extracted from completed runs. Accumulates traceable knowledge records across runs. Post-MVP capability.

**Planning layer** (external to DevOS): External planning tools (Linear, gstack, GitHub Issues) produce `change_intent.yaml`. DevOS does not own this layer.

## Execution Responsibility Model

| Actor | Role |
| --- | --- |
| **Agent Runtime** | Performs cognitive work. Produces all workflow artifacts. |
| **DevOS Kernel** | Deterministically governs workflow execution, gate validation, state transitions, and event recording. |
| **Human Decision Authority** | Optionally provides governance decisions (approvals/rejections) via `decision_log.yaml`. Never produces artifacts. |

Humans are governance participants, not workflow workers. Human interaction is optional — DevOS can operate fully autonomously when no gate requires a human decision.

## Documentation Directories

- `docs/vision`: System positioning, MVP scope, and long-term architectural direction.
- `docs/architecture`: Architecture references — integration model, agent contracts, LLM strategy, development pipeline, runtime module architecture.
- `docs/framework`: Core framework concepts — event model, workflow model, and knowledge/query contracts.
- `docs/runtime`: Runtime engine behavior, MVP execution scope, and module architecture.
- `docs/governance`: Boundaries, non-goals, anti-patterns, and project guardrails.
- `docs/roadmap`: Future-facing design ideas and parked capabilities not part of the MVP runtime.
- `docs/archive`: Historical plans, readiness notes, and implementation records retained for traceability.

## Recommended Reading Order for New Contributors

1. `docs/vision/product_vision.md` — What DevOS is, MVP scope, and non-goals.
2. `docs/vision/devos_kernel_architecture.md` — **Canonical four-system architecture reference** (start here for architecture).
3. `docs/vision/system_architecture.md` — System interaction diagram and layer detail.
4. `docs/architecture/system_map.md` — Concrete module map of all four systems.
5. `docs/architecture/development_pipeline.md` — Full planning-to-execution pipeline.
6. `docs/architecture/agent_contracts.md` — Agent contract model and Agent Runtime integration.
7. `docs/architecture/integration_model.md` — Artifact-first integration philosophy and adapter architecture.
8. `docs/architecture/devos_architecture.md` — Kernel module architecture reference.
9. `docs/framework/workflow_state_machine.md` — Workflow state machine visualization.
10. `docs/runtime/runtime_execution_model.md` — MVP runtime scope and future extension points.

After these, consult `docs/governance` for constraints, `docs/architecture/llm_strategy.md` for LLM independence, and `docs/roadmap` for future capabilities.

## Repository-to-Documentation Mapping

Documentation mirrors repository structure so that conceptual and implementation views stay aligned:

- `framework/` → specification and contract definitions
- `runtime/` → MVP workflow execution engine (see `runtime/README.md`)
- `integrations/` → external system adapters (future feature)
- `examples/` → example workspaces, sample inputs, and reproducible references

When searching for details, start with the corresponding `docs/*` section, then open the matching repository directory for implementation context.
