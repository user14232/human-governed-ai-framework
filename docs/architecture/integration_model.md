# DevOS – Integration Model

**Document type**: Architecture reference
**Status**: Normative for integration philosophy
**Date**: 2026-03-15

> For the four-system architecture (DevOS Kernel, Agent Runtime, Capability System, Knowledge System), see `docs/vision/devos_kernel_architecture.md`. This document describes the integration philosophy that governs how all four systems interact with each other and with external tools.

---

## 1. Core Principle: Artifact-First Integration

All integrations with DevOS must follow an **artifact-based interface**.

External tools, planning systems, agent frameworks, and LLM providers do not interact with DevOS through APIs, function calls, or shared state. They interact exclusively through artifacts on the filesystem.

```
External tool or system
         ↓
  produces an artifact
         ↓
DevOS artifact system
  (structural validation, hashing)
         ↓
gate evaluation
         ↓
workflow state transition
```

Artifacts are the universal interface. This is not a preference — it is an architectural constraint.

**Rationale**: Any component that produces a valid, schema-conformant artifact is a compatible integration target. DevOS does not need to know what produced an artifact. This makes the system tool-agnostic and replaceable at every layer.

**Source of truth rule**: External tools must never become the source of truth for DevOS workflow state. The DevOS run directory is always the authoritative state. External tools mirror DevOS state; they do not own it.

---

## 2. What DevOS Exposes to External Systems

DevOS exposes exactly two integration surfaces to external systems:

### Input surface

`change_intent.yaml` is the entry point for any DevOS run.

Any planning tool, issue tracker, or manual process that can produce a valid `change_intent.yaml` is compatible with DevOS. The format is defined at `framework/artifacts/schemas/change_intent.schema.yaml`.

### Output surface

The run directory at `runs/<run_id>/` contains:

- all produced artifacts
- the decision log
- the append-only event log
- run state

External systems that consume DevOS output (e.g., integration adapters, dashboards, knowledge systems) must read from this directory. They must not write to it except through the defined artifact schemas.

---

## 3. Adapter Architecture

External tools that need to interact with DevOS beyond reading run directories require an **adapter layer**.

Adapters translate between DevOS contracts and tool-specific execution interfaces.

### Adapter categories

| Adapter type | System | Purpose | Status |
| --- | --- | --- | --- |
| AgentAdapter | Agent Runtime | Translates DevOS agent contracts into agent invocation | Protocol defined in `runtime/agents/invocation_layer.py`; implementations are project-level |
| LLM provider adapter | Agent Runtime | Routes LLM invocations to local or cloud models | Post-MVP; see `docs/architecture/llm_strategy.md` |
| Capability adapter | Capability System | Wraps tool execution and exposes tools to agents | Post-MVP |
| Planning system adapter | Capability System | Converts planning tool output into `change_intent.yaml` | Post-MVP; manual conversion is the MVP approach |
| External state adapter | Capability System | Projects DevOS run state into external tools (e.g., Linear, GitHub Issues) | Post-MVP; see `docs/roadmap/integration_ecosystem_vision.md` |
| Knowledge extraction adapter | Knowledge System | Extracts knowledge records from terminal-state artifacts | Post-MVP; see `docs/framework/knowledge_query_contract.md` |

### Adapter rules

1. Adapters must not modify DevOS framework files.
2. Adapters must not write to run directories except by producing valid, schema-conformant artifacts.
3. Adapters must not alter workflow state directly. State transitions are the exclusive responsibility of the DevOS kernel.
4. Adapters must be stateless with respect to DevOS. They read contracts and write artifacts. They do not maintain their own state about run progress.

---

## 4. Planning System Integration

Planning tools sit outside the DevOS boundary.

The integration pattern for any planning system:

```
Planning system
  (epics / stories / tasks)
         ↓
task selection by human or automation
         ↓
change_intent.yaml authored or generated
         ↓
DevOS run initialized
```

The `change_intent.yaml` must be authored before a run begins. DevOS does not pull work items from planning systems during execution.

**Currently supported**: Manual authoring of `change_intent.yaml`.

**Future integration targets** (not yet implemented):
- Linear task to `change_intent.yaml` converter
- GitHub Issues to `change_intent.yaml` converter
- gstack task export

---

## 5. Agent Integration

Agents are integrated through the `AgentAdapter` protocol.

The protocol is defined in `runtime/agents/invocation_layer.py`. It specifies:

- how the kernel invokes an agent
- how the agent's output is consumed

The kernel does not know or care how an agent is implemented. The adapter is the isolation boundary.

The complete integration pattern from workflow state to artifact output:

```
DevOS workflow state
         ↓
agent contract (from framework/agents/)
         ↓
AgentAdapter
         ↓
External agent implementation
  (gstack agent / local LLM agent / human agent / script)
         ↓
Artifact output written to runs/<run_id>/artifacts/
         ↓
DevOS gate evaluates artifact
         ↓
Workflow state transitions
```

Example implementations of agent contracts:

- **gstack agents** — receive run context via adapter, produce artifacts, return to DevOS gate
- **local LLM agents** — adapter loads contract, prompts local model, parses structured output as artifact
- **human operator (development mode)** — reads contract and input artifacts, manually produces the output artifact; this is a bootstrap mode only, not intended for production operation
- **scripts** — deterministic transformation scripts that consume inputs and write output artifacts

DevOS governs the workflow. External systems perform the work.

**Currently implemented**: The `AgentAdapter` protocol (interface definition). No concrete adapters are part of the MVP runtime. See `docs/roadmap/future_features.md`.

---

## 6. Event-Driven Integration Surface

The DevOS event system provides a forward-compatible integration surface.

Every system action emits a typed event to `runs/<run_id>/events.jsonl`. Events are append-only and monotonically numbered.

External adapters that need to react to run state changes may read this event log. This is the correct integration pattern for dashboards, notification systems, and external state mirrors.

**Currently implemented**: Event emission to the local event log. No external event consumers are part of the MVP runtime.

**Future capability**: Event-driven adapters that consume this log and project run state into external tools. See `docs/roadmap/integration_ecosystem_vision.md`.

---

## 7. What Is Explicitly Excluded

The following integration patterns are **permanently excluded** from DevOS:

| Excluded pattern | Reason |
| --- | --- |
| Calling external APIs during run execution | Creates external dependencies that violate the local-only, deterministic execution model |
| Pulling work items from planning tools at runtime | DevOS does not pull; it consumes `change_intent.yaml` which is produced before run start |
| Writing run state to external databases | All run state lives on the filesystem; no external state store |
| Allowing external tools to trigger workflow transitions | Only the DevOS CLI may advance a run; external tools produce artifacts at most |
| Implicit artifact production | All artifacts must be explicitly written by an agent or adapter and validated by the artifact system |

---

## 8. Integration Readiness in the MVP

The following integration points are present in the MVP runtime and are ready for future activation:

| Integration point | Location | Current state |
| --- | --- | --- |
| `AgentAdapter` protocol | `runtime/agents/invocation_layer.py` | Interface defined; no concrete adapters built |
| `InvocationMode.AUTOMATED` code path | `runtime/agents/invocation_layer.py` | Code path exists; not activated |
| Knowledge extraction trigger events | `runtime/knowledge/extraction_hooks.py` | Events emitted at terminal states; no extraction performed |
| Artifact schema validation | `runtime/artifacts/artifact_system.py` | Structural validation active; semantic validation is future |
| Event log | `runs/<run_id>/events.jsonl` | Emitted; no external consumers in MVP |

---

## Further Reading

- `docs/vision/devos_kernel_architecture.md` — Canonical four-system architecture reference
- `docs/architecture/system_map.md` — Concrete module map of all four systems
- `docs/architecture/agent_contracts.md` — Agent contract model and Agent Runtime integration
- `docs/architecture/llm_strategy.md` — LLM independence and provider abstraction
- `docs/architecture/development_pipeline.md` — Full planning-to-execution pipeline
- `docs/framework/knowledge_query_contract.md` — Knowledge System contract (post-MVP)
- `docs/roadmap/future_features.md` — Parked integration features
- `docs/roadmap/integration_ecosystem_vision.md` — Future integration ecosystem vision
