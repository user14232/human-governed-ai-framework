# DevOS – Product Vision (MVP)

**Document type**: Product vision  
**Status**: Normative for MVP scope  
**Date**: 2026-03-15

---

## 1. What DevOS Is

DevOS is a **workflow governance kernel for AI-assisted engineering**.

It governs how development work progresses through explicit states, artifacts, and human decisions. DevOS sits between planning systems and AI execution systems. It orchestrates work but does not perform reasoning itself. External tools perform reasoning, planning, and code generation. DevOS governs the workflow.

DevOS treats each piece of development work as a **run**: a scoped execution of a defined workflow that produces structured artifacts and records explicit decisions.

---

## 2. MVP Scope

The DevOS MVP is a **CLI-based workflow governance tool**.

It supports a minimal, deterministic execution model:

```
INIT → PLANNING → IMPLEMENTING → REVIEWING → ACCEPTED
```

The MVP runtime implements exactly these core concepts:

| Concept | Role |
| --- | --- |
| **Run** | Scoped execution unit for one change intent |
| **Workflow** | State machine defining how work progresses |
| **Artifact** | Structured file produced at each stage |
| **Decision** | Explicit human authorization recorded in `decision_log.yaml` |
| **Event** | Append-only record of every system action |

The MVP runtime components are:

- `run_engine` — run lifecycle, initialization, terminal state detection
- `workflow_engine` — state machine traversal, one transition per invocation
- `gate_evaluator` — four-step gate validation before each transition
- `artifact_system` — artifact storage, hashing, structural validation
- `decision_system` — decision log reading, typed signal return
- `event_system` — event construction, monotonic ID assignment, persistence
- `cli` — command-line interface (`run`, `resume`, `status`, `check`, `advance`)

---

## 3. Key Principles

### Deterministic workflows

Workflow progression is governed by explicit gate conditions. Every transition requires artifact presence, structural validation, and optionally a governance approval. No transition is implicit or inferred.

### Agents perform cognitive work; agents produce all artifacts

Each workflow stage is executed by an agent or automated tool. Agents perform reasoning, synthesis, and generation. All artifacts produced in a run are produced by agents or automated tools. Humans never produce workflow artifacts directly.

### Agents are used only for cognitive tasks

Agents are invoked for tasks that require reasoning, synthesis, or language generation. All workflow orchestration, gate validation, and state management is implemented as deterministic runtime logic. Agents do not control workflow execution, system state, or runtime governance.

### Artifacts capture reasoning

Each workflow stage produces one or more structured artifacts. Artifacts are the sole communication channel between stages and the durable trace of all work and reasoning.

### Explicit governance decisions

All approvals and rejections are recorded as explicit entries in an append-only `decision_log.yaml`. The runtime never infers or grants approvals. No artifact can advance past a configured approval gate without a matching decision entry. Human interaction is optional — when no gate requires a decision, DevOS operates without human input.

### Humans are governance participants, not workflow workers

The `human_decision_authority` actor interacts with DevOS only through `decision_log.yaml`. Humans do not produce artifacts, execute agent roles, or drive workflow execution.

### Filesystem-based execution

All run state — artifacts, decisions, events — lives on the filesystem under `runs/<run_id>/`. No database, no hidden state. Any run can be fully reconstructed from its directory.

---

## 4. What DevOS Is Not

| Common assumption | DevOS stance |
| --- | --- |
| A Git replacement | DevOS does not manage version control. It governs how development work progresses, not how code is stored. |
| An autonomous agent orchestrator | DevOS does not drive autonomous AI loops. Agents are invoked once per stage. Humans may provide decisions at governance gates, but are not required for every transition. DevOS can operate fully autonomously when no gate requires a human decision. |
| An AI memory or knowledge system | DevOS does not maintain persistent AI context, manage embeddings, or provide semantic retrieval. Knowledge extraction is a future capability, not an MVP feature. |
| A planning system | DevOS does not define what should be built. It executes governance over work items produced by external planning tools. |
| An AI reasoning engine | DevOS does not perform AI reasoning. Reasoning occurs in external agent implementations behind the `AgentAdapter` protocol. |
| A platform or microservice | DevOS is a single CLI tool operating on a local project directory. It has no server component and requires no external service. |

---

## 5. Design Boundaries

The runtime is intentionally minimal. It must remain:

- **Deterministic**: identical inputs always produce identical outputs and state transitions.
- **Reproducible**: any run can be resumed or audited from the filesystem alone.
- **Tool-agnostic**: the runtime has no knowledge of how agents are implemented. The `AgentAdapter` protocol isolates invocation mechanisms from the engine.
- **LLM-independent**: the kernel contains no LLM SDK imports. All AI interaction occurs in external adapters behind the `AgentAdapter` protocol.
- **Non-autonomous**: the CLI advances one transition per invocation. There is no run-until-done loop. A human operator or controlled wrapper script calls `advance` iteratively. Human presence is not required at every gate — when gates are satisfied by artifact conditions alone, autonomous iteration by a wrapper script is valid.
- **Planning-independent**: the kernel has no knowledge of the planning tool that produced `change_intent.yaml`.

Complexity must not be added to the runtime core. New capabilities belong in the framework layer (contracts, schemas) or in the roadmap.

---

## 6. Relationship to the Framework Layer

The framework layer defines the normative rules that all runtime implementations must satisfy:

- workflow YAML definitions (`framework/workflows/`)
- artifact schemas (`framework/artifacts/schemas/`)
- agent role contracts (`framework/agents/`)
- system invariants and governance contracts (`framework/contracts/`)

The runtime reads the framework layer at initialization and executes against it. The framework is never modified during execution.

---

## 7. System Positioning

DevOS is a **deterministic workflow governance kernel for AI-assisted engineering**. It sits between planning systems and agent execution systems. It does not belong to either.

```
Planning Layer
    (gstack / Linear / GitHub Issues / any task system)
         ↓
DevOS Governance Kernel
    (run lifecycle / workflow transitions / artifact validation / decision logging)
         ↓
Agent Execution Layer
    (gstack agents / local LLM agents / scripted tools / automated adapters)
         ↓
Engineering Tool Layer
    (Git / pytest / Ruff / CI pipelines / IDE assistants)
```

This is the defining architectural separation. DevOS sits in the middle and governs the process. It does not belong to the planning layer, the agent layer, or the tooling layer.

---

## 8. DevOS Coordinates — It Does Not Replace

DevOS coordinates external tools. It does not implement them or replace them.

| Concern | Owner | DevOS role |
| --- | --- | --- |
| **Planning** | External planning systems (gstack, Linear, GitHub Issues) | Consumes their output as `change_intent.yaml` |
| **AI reasoning** | External agents (gstack agents, local LLMs, cloud models, automated tools) | Governs their invocation through contracts and adapters |
| **Code execution** | External tools (Git, pytest, Ruff, CI systems) | Evaluates their output artifacts at gate checks |
| **Governance** | DevOS kernel | Owns entirely |

DevOS does not replace:

- **Version control** — DevOS governs change intent, not code storage. Git remains the version control system.
- **AI agents** — DevOS defines agent contracts but does not implement agent reasoning. Reasoning happens in external systems.
- **Planning systems** — DevOS does not define what should be built. It executes governance over work items that planning tools produce.
- **IDEs or coding tools** — DevOS does not generate code. Code generation is the responsibility of AI agents and automated tools.

Any tool that can produce a schema-conformant artifact is compatible with DevOS. DevOS provides discipline and traceability across these tools without requiring tight integration with any of them.

The full architectural picture is documented at `docs/vision/system_architecture.md`.

---

## 9. Roadmap

Future capabilities are documented and explicitly parked outside the MVP runtime. They are not excluded by design flaw — they are excluded to keep the MVP small, stable, and shippable.

Future extension areas include:
- concrete `AgentAdapter` implementations (gstack, Cursor, local LLM)
- LLM provider abstraction layer with local and cloud model support
- knowledge record extraction and indexing from run artifacts
- external tool adapters (Linear, GitHub Issues, CI/CD systems)
- automated improvement cycle triggering
- capability plugin system for extended gate validation

See `docs/roadmap/future_features.md` for the full roadmap inventory.
