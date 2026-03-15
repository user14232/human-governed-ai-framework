# DevOS — Kernel Architecture

**Document type**: Canonical architecture reference
**Status**: Normative
**Date**: 2026-03-15

> This is the canonical reference for the DevOS system architecture. All other architecture documents derive from or are consistent with this model. When documents conflict, this document takes precedence.

---

## 1. System Overview

DevOS is a **workflow governance kernel for AI-assisted engineering**.

It enforces deterministic workflow execution, artifact traceability, and decision governance over AI-assisted development processes. DevOS does not perform reasoning, generate code, or manage external tools. It governs how work progresses through explicit states, artifacts, and decisions.

DevOS consists of four distinct systems:

| System | Role |
| --- | --- |
| **DevOS Kernel** | Deterministic governance core — run lifecycle, workflow execution, gate validation, artifact validation, event logging |
| **Agent Runtime** | AI reasoning execution — agent selection, context building, LLM invocation, artifact production |
| **Capability System** | Tool access for agents — Git, Linear, filesystem, MCP servers, codebase analysis |
| **Knowledge System** | Persistent engineering memory — knowledge extraction, indexing, and deterministic query |

Each system has clearly bounded responsibilities. No system substitutes for another.

---

## 2. System Interaction Diagram

```
Planning Layer (external)
  Linear / GitHub Issues / gstack / manual authoring
         ↓
  change_intent.yaml
         ↓
┌─────────────────────────────────────────────────────────┐
│                     DevOS Kernel                        │
│                                                         │
│   Run Engine → Workflow Engine → Gate Evaluator         │
│          ↓              ↓              ↓                │
│   Artifact System    Event System   Decision System     │
│          ↓                                              │
│   AgentAdapter ──────────────────────────────────────┐  │
└──────────────────────────────────────────────────────┼──┘
                                                       ↓
┌──────────────────────────────────────────────────────────┐
│                     Agent Runtime                        │
│                                                         │
│   Context Builder → LLM / Agent invocation              │
│                          ↓                              │
│              Artifact output (schema-conformant)        │
│                          ↓  ──────────────────────┐     │
└──────────────────────────────────────────────────  ↓ ───┘
                                                     │
              ┌──────────────────────────────────────┤
              ↓                                      ↓
┌─────────────────────────┐          ┌───────────────────────┐
│   Capability System     │          │   Knowledge System    │
│                         │          │                       │
│  Git / Linear / MCP     │          │  Extractor / Index /  │
│  Filesystem / Analysis  │          │  Query Engine         │
└─────────────────────────┘          └───────────────────────┘
              ↑                                      ↑
              │                              (terminal state)
              └──── agents call capabilities ────────┘
```

**Data flow**: `change_intent.yaml` enters the Kernel → Kernel invokes Agent Runtime via adapter → Agent Runtime uses Capability System → Agent Runtime produces artifacts → Kernel validates artifacts via gate → Kernel advances workflow state → at terminal state, Knowledge System extracts from artifacts.

All inter-system communication occurs through artifacts on the filesystem. There are no direct API calls between systems.

---

## 3. System Responsibilities

### 3.1 DevOS Kernel

The DevOS Kernel is the **deterministic governance core** of DevOS.

**The Kernel is responsible only for:**

| Responsibility | Description |
| --- | --- |
| Run lifecycle | Initialization, resumption, terminal state detection |
| Workflow execution | State machine traversal, one transition per invocation |
| Gate validation | Four-step gate check before every state transition |
| Artifact validation | Structural validation against schemas; SHA-256 hashing |
| Event logging | Append-only recording of every system action |

**The Kernel does not:**

- Perform AI reasoning
- Generate code or artifacts
- Call LLM APIs
- Manage external tools
- Implement agent logic
- Perform knowledge extraction

The Kernel's only job is deterministic workflow control. It must remain minimal, stable, and free of external service dependencies.

**Kernel modules:**

```
runtime/engine/run_engine.py       — run lifecycle
runtime/engine/workflow_engine.py  — state machine traversal
runtime/engine/gate_evaluator.py   — gate validation
runtime/artifacts/artifact_system.py — artifact storage and validation
runtime/events/event_system.py     — event logging
```

**Kernel rules:**

- One transition per `advance` invocation — no autonomous loops
- No hidden state — all state is reconstructed from the filesystem
- No semantic interpretation — the Kernel validates structure, not content
- No implicit approvals — all gate approvals require an explicit `decision_log.yaml` entry
- No external service dependency — DevOS must operate entirely from the local filesystem

---

### 3.2 Agent Runtime

The Agent Runtime is responsible for **AI reasoning execution**.

**Responsibilities:**

- Selecting the correct agent for a workflow state
- Building context from run artifacts and domain inputs
- Invoking LLMs, external agents, or scripted tools
- Producing schema-conformant artifacts
- Calling Capability System tools when agent tasks require them

**The Agent Runtime is invoked by the Kernel through the `AgentAdapter` protocol.** The Kernel does not implement reasoning logic. It only invokes adapters and validates the resulting artifacts.

**Possible Agent Runtime implementations:**

| Implementation | Description |
| --- | --- |
| Cursor agents | IDE-native agents receiving run context and agent contracts |
| gstack agents | AI-backed agents producing structured artifacts |
| Local LLM agents | Adapters calling Ollama or vLLM with structured prompts |
| Cloud LLM agents | Adapters calling remote model APIs |
| Scripted tools | Deterministic programs transforming input artifacts to output artifacts |
| Human operator (dev mode) | Bootstrap mode only — human reads contract and writes artifact directly |

The `AgentAdapter` protocol is the **isolation boundary** between the Kernel and all Agent Runtime implementations. The Kernel sees only the resulting artifact.

**Key constraint:** Agents do not control workflow execution. The Kernel governs all state transitions. Agents produce artifacts; the Kernel validates them and decides whether to advance.

---

### 3.3 Capability System

The Capability System provides **tool access for agents**.

Capabilities are external tool integrations that agents invoke while performing their work. The Kernel has no knowledge of which capabilities an agent uses.

**Examples of capabilities:**

| Capability | Description |
| --- | --- |
| Git operations | Branch creation, commit, status checking |
| Linear ticket management | Reading and updating work items |
| Filesystem access | Reading project files, writing to workspace |
| Codebase analysis | AST parsing, dependency analysis, linting |
| MCP server tools | Tools exposed through the Model Context Protocol |

**Capability implementation options:**

- Python APIs called by agent adapters
- CLI tools wrapped by the adapter
- MCP servers providing structured tool APIs
- Service adapters for external systems

**The Kernel must remain agnostic to capability implementations.** Capabilities are a concern of the Agent Runtime adapter layer, not the Kernel.

**Capability discovery**: Projects declare their available capabilities in `framework/contracts/capabilities.yaml`. The Kernel does not load or process this file during execution — it is consumed by agent adapters.

---

### 3.4 Knowledge System

The Knowledge System provides **persistent engineering memory**.

**Responsibilities:**

- Extracting structured knowledge records from completed run artifacts
- Maintaining a project-scoped knowledge index across runs
- Enabling deterministic, exact-match knowledge queries
- Providing relevant context to agents at the start of subsequent runs

**Key constraints:**

- Knowledge records must maintain traceable provenance to specific artifacts and runs
- The Knowledge System must not alter original artifacts
- All extraction is triggered at terminal states — knowledge is accumulated, not generated during execution
- Queries are deterministic exact-match operations — no heuristic or semantic search

**Integration with the Kernel:** The Kernel emits `knowledge.extraction_triggered` events at terminal states via `runtime/knowledge/extraction_hooks.py`. The Knowledge System reacts to these events. This is the only coupling point.

**Current state**: The MVP Kernel emits trigger events. Full extraction, indexing, and querying are post-MVP capabilities documented in `docs/roadmap/future_features.md`.

---

## 4. Architectural Separation

The four systems must remain cleanly separated:

| Boundary | Rule |
| --- | --- |
| Kernel ↔ Agent Runtime | The Kernel invokes agents only through the `AgentAdapter` protocol. No reasoning logic in the Kernel. |
| Kernel ↔ Capability System | The Kernel has no knowledge of capabilities. Capabilities are invoked by agents, not the Kernel. |
| Kernel ↔ Knowledge System | The Kernel only emits trigger events. It does not extract, index, or query knowledge. |
| Agent Runtime ↔ Kernel | Agents produce artifacts. They do not advance workflow state, modify framework files, or write to the decision log. |
| All systems ↔ All systems | All inter-system communication occurs through artifacts on the filesystem. |

**Artifact-first principle**: Artifacts are the only communication interface between system components. External systems interact with DevOS by producing schema-conformant artifacts. There are no shared API calls, shared state, or function call interfaces between systems.

---

## 5. Design Principles

### Deterministic governance over autonomous agents

DevOS prioritizes deterministic, reproducible workflows over autonomous agent behavior. Agents produce artifacts. The Kernel controls workflow progression. No system component may alter workflow state through side effects.

### Artifact-first integration

Artifacts are the sole communication interface between all system components. This makes every system independently replaceable and the overall system auditable.

### Separation of reasoning and control

AI reasoning occurs in the Agent Runtime. System control occurs in the Kernel. These responsibilities must never be mixed. An agent that attempts to control workflow execution is a contract violation.

### Provider independence

DevOS must remain independent of LLM providers. All model interaction must occur in Agent Runtime adapters, outside the Kernel. The Kernel has no knowledge of which model was used, which API was called, or how many tokens were consumed.

### Kernel minimalism

The Kernel must remain minimal and stable. New capabilities must be implemented in the Agent Runtime, Capability System, or Knowledge System — not in the Kernel. The Kernel's module inventory (run engine, workflow engine, gate evaluator, artifact system, event system) is stable.

### Filesystem as the system of record

All state — artifacts, decisions, events, run state — lives on the local filesystem. No external database. No external state store. DevOS must be fully reconstructable from the run directory.

---

## 6. The Four-System Architecture at a Glance

```
DevOS Kernel          — enforces workflow, validates artifacts, logs events
Agent Runtime         — performs reasoning, produces artifacts
Capability System     — provides tool access for agents
Knowledge System      — accumulates traceable engineering memory
```

These four systems, combined with the Planning Layer (external) and the Human Decision Authority (governance actor), form the complete DevOS operating model.

---

## Further Reading

- `docs/vision/product_vision.md` — MVP scope, principles, and non-goals
- `docs/vision/system_architecture.md` — System interaction diagram (four-layer view)
- `docs/architecture/system_map.md` — Concrete module map of all four systems
- `docs/architecture/agent_contracts.md` — Agent contract model and Agent Runtime integration
- `docs/architecture/integration_model.md` — Artifact-first integration philosophy
- `docs/architecture/llm_strategy.md` — LLM independence and provider abstraction
- `docs/architecture/devos_architecture.md` — Kernel module architecture reference
- `docs/framework/knowledge_query_contract.md` — Knowledge System contract (future capability)
- `docs/roadmap/future_features.md` — Capabilities parked outside the MVP
