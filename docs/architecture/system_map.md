# DevOS — System Map

**Document type**: Architecture reference
**Status**: Normative for system structure
**Date**: 2026-03-15

> This document maps every module and component to its owning system. It is derived from the canonical architecture in `docs/vision/devos_kernel_architecture.md`. Consult that document for responsibility definitions and design principles.

---

## DevOS Kernel

The governance core. Deterministic. No AI reasoning. No external service dependencies.

```
runtime/engine/
    run_engine.py           — Run lifecycle: init, resume, terminal detection
    workflow_engine.py      — State machine traversal; one transition per advance()
    gate_evaluator.py       — Four-step gate validation before every transition

runtime/artifacts/
    artifact_system.py      — Artifact registration, structural validation, SHA-256 hashing, immutability

runtime/events/
    event_system.py         — Event construction, monotonic ID assignment, envelope validation
    metrics_writer.py       — Atomic append-only writes to run_metrics.json

runtime/decisions/
    decision_system.py      — Decision log reading; returns typed signals; never writes to decision log

runtime/store/
    run_store.py            — Run directory layout, path resolution, run enumeration
    file_store.py           — Atomic file I/O, SHA-256 hashing, JSON/YAML parsing

runtime/types/
    run.py                  — RunId, RunContext, RunState, TERMINAL_STATES
    workflow.py             — WorkflowDefinition, Transition, RequiresBlock
    artifact.py             — ArtifactRef, ArtifactId, ArtifactHash, ArtifactStatus
    event.py                — EventEnvelope, EventType
    decision.py             — DecisionEntry, DecisionType, DecisionReference
    gate.py                 — GateResult, GateCheckDetail, CheckType, CheckResult

runtime/framework/
    workflow_loader.py      — Parses workflow YAML definitions into WorkflowDefinition
    schema_loader.py        — Loads artifact schemas from framework/artifacts/schemas/
    agent_loader.py         — Loads agent role contracts from framework/agents/

runtime/cli.py              — Five commands: run, resume, status, check, advance
```

**Kernel contracts** (normative specifications consumed by the Kernel):

```
framework/contracts/runtime_contract.md
framework/contracts/system_invariants.md
framework/contracts/framework_validation_contract.md
framework/contracts/framework_versioning_policy.md
framework/contracts/migration_contract.md
framework/contracts/domain_input_contracts.md
framework/contracts/artifact_status_model.md
framework/workflows/default_workflow.yaml
framework/workflows/release_workflow.yaml
framework/artifacts/schemas/              — all schema definitions
```

---

## Agent Runtime

AI reasoning execution. Invoked by the Kernel through the `AgentAdapter` protocol. Produces artifacts.

```
runtime/agents/
    invocation_layer.py     — AgentAdapter protocol; MANUAL and AUTOMATED invocation modes

runtime/knowledge/
    extraction_hooks.py     — Extraction trigger events at terminal states (Kernel-side integration point)
```

**Agent contracts** (consumed by Agent Runtime implementations):

```
framework/agents/
    agent_orchestrator.md
    agent_planner.md
    agent_architecture_guardian.md
    agent_test_designer.md
    agent_test_author.md
    agent_test_runner.md
    agent_branch_manager.md
    agent_implementer.md
    agent_reviewer.md
    agent_reflector.md
    agent_improvement_designer.md
    agent_work_item_author.md
    agent_release_manager.md
    human_decision_authority.md   — governance actor (not an autonomous agent)
```

**Prompt builders** (Agent Runtime implementation support):

```
runtime/agents/prompt_builder.py    — Context and prompt construction for LLM-backed adapters
runtime/agents/llm_client.py        — LLM provider client interface
runtime/agents/llm_adapter.py       — LLM provider adapter implementations
runtime/agents/artifact_parser.py   — Parses LLM output into schema-conformant artifacts
```

**Agent Runtime implementations** (project-level or external — not part of the MVP kernel):

| Implementation | Description |
| --- | --- |
| Cursor agents | IDE-native agents receiving run context |
| gstack agents | AI-backed structured-output agents |
| Local LLM adapters | Ollama / vLLM backed adapters |
| Cloud LLM adapters | Remote model API adapters |
| Scripted tools | Deterministic transformation programs |

---

## Capability System

Tool access for agents. The Kernel is agnostic to all capability implementations.

```
framework/contracts/capability_integration_contract.md   — rules for capability integration
framework/contracts/capabilities.yaml                    — capability interface definitions
framework/artifacts/schemas/capability_registry.schema.yaml
```

**Implemented integrations:**

```
integrations/planning/
    planning_engine.py      — Deterministic planning layer (Linear → change_intent.yaml)
    planning_models.py      — Planning data models
    planning_parser.py      — Planning input parser
    work_item_linter.py     — Work item semantic validation

integrations/linear/linear_project_creator/
    README.md               — Full Linear project creator documentation
    contracts/work_item_contract.md
    contracts/work_item_linter_rules.md
    prompts/epic_generation_prompt.md
    prompts/story_generation_prompt.md
    quality/story_quality_checklist.md
    quality/task_quality_checklist.md
```

**Capability categories** (future implementations):

| Category | Examples |
| --- | --- |
| Version control | Git branch management, commit, status |
| Issue tracking | Linear, GitHub Issues |
| Filesystem | Project file access, workspace reads |
| Code analysis | AST parsing, linting, dependency graphs |
| MCP tools | Any tool exposed via Model Context Protocol |
| CI/CD | GitHub Actions, GitLab CI integration |

---

## Knowledge System

Persistent engineering memory. Accumulates traceable records from completed runs.

```
framework/artifacts/schemas/
    knowledge_record.schema.json    — Schema for a single knowledge record
    knowledge_index.schema.json     — Schema for the project knowledge index
    reflection_notes.schema.md      — Schema for reflection output (improvement cycle)
    improvement_proposal.schema.md  — Schema for improvement proposals

framework/workflows/improvement_cycle.yaml  — Improvement cycle workflow definition

framework/agents/
    agent_reflector.md              — Improvement cycle REFLECT state contract
    agent_improvement_designer.md   — Improvement cycle PROPOSE state contract
```

**Contracts:**

```
docs/framework/knowledge_query_contract.md  — Normative extraction and query contract
docs/framework/event_model.md               — Event envelope definitions (feeds extraction)
```

**Knowledge System components** (post-MVP — not part of current implementation):

| Component | Description |
| --- | --- |
| Knowledge Extractor | Reads terminal-state artifacts, produces typed knowledge records |
| Knowledge Index | Project-scoped accumulation of knowledge records across runs |
| Query Engine | Deterministic exact-match query interface over the knowledge index |
| Provenance Tracker | Maintains artifact_hash and run_id traceability for every record |

**Current state**: The MVP Kernel emits `knowledge.extraction_triggered` events at terminal states (`runtime/knowledge/extraction_hooks.py`). Full Knowledge System extraction, indexing, and querying are post-MVP capabilities. See `docs/roadmap/future_features.md`.

---

## Cross-Cutting

Components and contracts that apply to all systems.

```
framework/contracts/system_invariants.md        — Non-negotiable system-wide invariants
framework/artifacts/schemas/event_envelope.schema.json
framework/artifacts/schemas/run_metrics.schema.json
framework/artifacts/schemas/decision_log.schema.yaml
framework/artifacts/schemas/orchestrator_log.schema.md

docs/governance/anti_patterns_and_non-goals.md  — Governance boundaries and forbidden patterns
docs/framework/workflow_state_machine.md        — Workflow state machine visualization
```

---

## Workspace Layout

The DevOS workspace is the filesystem boundary that all four systems share.

```
<project>/
    inputs/                         — mandatory and optional project inputs
        domain_scope.md
        domain_rules.md
        source_policy.md
        glossary.md
        architecture_contract.md

    planning/                       — planning artifacts (optional)
        *.yaml

    runs/
        <run_id>/
            artifacts/              — all workflow artifacts (agent outputs)
            decision_log.yaml       — human governance decisions (append-only)
            run_metrics.json        — events and invocation records (append-only)
            run_state.json          — current run state

    .devos/
        config.yaml                 — project configuration
```

---

## Further Reading

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture reference
- `docs/vision/system_architecture.md` — System interaction diagram
- `docs/architecture/devos_architecture.md` — Kernel module architecture reference
- `docs/architecture/agent_contracts.md` — Agent contract model
- `docs/architecture/integration_model.md` — Artifact-first integration philosophy
- `docs/framework/knowledge_query_contract.md` — Knowledge System contract
- `docs/runtime/runtime_module_architecture.md` — Full module interface signatures
