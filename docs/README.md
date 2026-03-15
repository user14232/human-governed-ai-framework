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

## DevOS System Layers

- **Planning layer**: External planning tools (Linear, gstack, GitHub Issues) produce `change_intent.yaml`. DevOS does not own this layer.
- **Governance kernel**: The DevOS runtime — run lifecycle, workflow transitions, gate evaluation, artifact validation, decision logging, event tracking. All orchestration and system control is deterministic runtime logic.
- **Agent execution layer**: External agents implement DevOS contracts and produce all workflow artifacts. Agents are used only for cognitive tasks (reasoning, synthesis, generation). DevOS invokes them through the `AgentAdapter` protocol.
- **Tooling layer**: External tools (Git, Pytest, Ruff, Semgrep) perform concrete tasks and produce artifacts consumed by DevOS gates.

## Execution Responsibility Model

| Actor | Role |
| --- | --- |
| **Agents** | Perform cognitive work. Produce all workflow artifacts. |
| **DevOS runtime** | Deterministically govern workflow execution, gate validation, state transitions, and event recording. |
| **Human Decision Authority** | Optionally provide governance decisions (approvals/rejections) via `decision_log.yaml`. Never produce artifacts. |

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
2. `docs/vision/system_architecture.md` — Four-layer system architecture and governance kernel detail.
3. `docs/architecture/development_pipeline.md` — Full planning-to-execution pipeline.
4. `docs/architecture/agent_contracts.md` — Agent contract model and external implementations.
5. `docs/architecture/integration_model.md` — Artifact-first integration philosophy and adapter architecture.
6. `docs/architecture/devos_architecture.md` — Runtime module architecture reference.
7. `docs/framework/workflow_state_machine.md` — Workflow state machine visualization.
8. `docs/runtime/runtime_execution_model.md` — MVP runtime scope and future extension points.

After these, consult `docs/governance` for constraints, `docs/architecture/llm_strategy.md` for LLM independence, and `docs/roadmap` for future capabilities.

## Repository-to-Documentation Mapping

Documentation mirrors repository structure so that conceptual and implementation views stay aligned:

- `framework/` → specification and contract definitions
- `runtime/` → MVP workflow execution engine (see `runtime/README.md`)
- `integrations/` → external system adapters (future feature)
- `examples/` → example workspaces, sample inputs, and reproducible references

When searching for details, start with the corresponding `docs/*` section, then open the matching repository directory for implementation context.
