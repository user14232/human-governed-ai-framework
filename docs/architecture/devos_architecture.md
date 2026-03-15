# DevOS — System Architecture

**Status:** Non-normative reference document
**Normative source:** `contracts/`

This document describes the system architecture of DevOS. It consolidates the architecture
narrative from the engineering specifications in `docs/phase3_runtime_realization_plan.md`
and `docs/runtime_module_architecture.md` into a single reference document.

This document is **non-normative**. The normative runtime rules remain in `contracts/`.

---

## 1. System Layers

DevOS operates through three conceptual layers:

```
Framework
    ↓
Workflows
    ↓
Runs
```

| Layer | Role | Location |
| --- | --- | --- |
| **Framework** | Kernel rules: invariants, artifact contracts, agent role definitions, governance rules | `contracts/`, `agents/`, `artifacts/schemas/` |
| **Workflows** | State machines that define how development work progresses | `workflow/` |
| **Runs** | Concrete executions of workflows, producing artifacts and decisions | `runs/<run_id>/` (project-level) |

The **framework layer** acts as the DevOS kernel. It cannot be modified during execution.
Workflow definitions and agent contracts are loaded once at runtime initialization and
treated as read-only.

---

## 2. Engineering OS Mental Model

DevOS maps to the conceptual model of a traditional operating system:

| OS Concept | DevOS Equivalent |
| --- | --- |
| Process | Run |
| Program | Workflow |
| Worker | Agent |
| Filesystem | Artifacts |
| System Log | Events |
| System Memory | Knowledge |
| Kernel Rules | System Invariants |

Agents do not control execution. They are invoked by the workflow engine, produce
artifacts, and terminate. Workflow progression is governed by gate validation and
human decisions — not by agents.

---

## 3. Execution Model

The DevOS execution model is:

```
Run → Workflow → Agent → Artifact → Decision → Event → Knowledge
```

Each element serves a specific role:

| Element | Role |
| --- | --- |
| **Run** | Scoped execution unit bound to a single `change_intent.yaml` |
| **Workflow** | Orchestration engine; sequences agent invocations via state transitions |
| **Agent** | Single-shot task executor; produces one or more defined artifacts |
| **Artifact** | Structured output; sole communication channel between system components |
| **Decision** | Explicit human authorization; recorded append-only in `decision_log.yaml` |
| **Event** | Append-only timeline record of every system action |
| **Knowledge** | Extracted, traceable records derived from artifacts after run completion |

**Key constraint:** Agents do not control execution. The workflow engine governs all
state transitions. Gate validation must pass before any transition proceeds.

---

## 4. Run Lifecycle

### Primary Delivery Cycle

```
INIT
→ PLANNING
→ ARCH_CHECK
→ TEST_DESIGN
→ BRANCH_READY
→ IMPLEMENTING
→ TESTING
→ REVIEWING
→ ACCEPTED | ACCEPTED_WITH_DEBT | FAILED
```

`FAILED` is a terminal state. A new run (new `run_id`) is required for any rework.

`ACCEPTED_WITH_DEBT` requires explicit human approval.

`ARCH_CHECK` is blocked until `arch_review_record.md` has `outcome: PASS`. If outcome is
`CHANGE_REQUIRED`, an `architecture_change_proposal.md` must be produced, approved, and a
new `arch_review_record.md` with `outcome: PASS` must be recorded before the run may proceed.

### Improvement Cycle

```
OBSERVE
→ REFLECT
→ PROPOSE
→ HUMAN_DECISION
→ (optional) new_change_intent
```

The improvement cycle is a separate run with its own `run_id`. It requires
`run_metrics.json` from a completed prior run. The cycle produces an
`improvement_proposal.md` that must be explicitly approved before any resulting
change intent is created.

### Release Workflow (opt-in)

```
RELEASE_INIT
→ RELEASE_PREPARING
→ RELEASE_REVIEW
→ RELEASED | RELEASE_FAILED
```

The release workflow is a separate opt-in run with its own `run_id`.
`RELEASE_FAILED` on explicit rejection is terminal.

---

## 5. Data Flow

Artifacts are produced sequentially as the run progresses through states.
Each artifact is the input to the next workflow stage.

```
change_intent.yaml
    → implementation_plan.yaml
    → design_tradeoffs.md
    → arch_review_record.md
    → test_design.yaml
    → branch_status.md
    → implementation_summary.md
    → test_report.json
    → review_result.md
    → run_metrics.json
```

Supporting artifacts:

- `architecture_change_proposal.md` — produced when `ARCH_CHECK` yields `CHANGE_REQUIRED`
- `decision_log.yaml` — append-only; records all human approvals and decisions
- `orchestrator_log.md` — produced by `agent_orchestrator` as an execution trace

All artifacts reside under: `runs/<run_id>/artifacts/`

`decision_log.yaml` resides at: `runs/<run_id>/decision_log.yaml`

No artifact may be modified after it has been approved
(see `contracts/runtime_contract.md` Section 3).

---

## 6. Runtime Modules

The DevOS runtime is decomposed into 12 modules across 6 layers. The complete
specification with Python-style interface signatures is in `docs/runtime_module_architecture.md`.

### Layer 1 — Types (`runtime/types/`)

Frozen value objects. No external dependencies. No behavior beyond validation.

| Module | Responsibility |
| --- | --- |
| `run` | Run identity, state, metadata |
| `workflow` | Workflow state, transition definitions |
| `artifact` | Artifact metadata, status |
| `event` | Event envelope structure |
| `decision` | Decision entry, approval binding |
| `gate` | Gate check input/output contracts |

### Layer 2 — Framework Loaders (`runtime/framework/`)

Read-only parsers. Called once at runtime initialization.

| Module | Responsibility |
| --- | --- |
| `workflow_loader` | Parses and validates `workflow/*.yaml` definitions |
| `schema_loader` | Loads artifact schemas from `artifacts/schemas/` |
| `agent_loader` | Loads agent role contracts from `agents/` |

### Layer 3 — Store (`runtime/store/`)

Pure filesystem abstraction. No business logic.

| Module | Responsibility |
| --- | --- |
| `run_store` | Run directory layout, run state persistence |
| `file_store` | Artifact read/write, hash computation (SHA-256) |

### Layer 4 — Engine (`runtime/engine/`)

Core execution logic.

| Module | Responsibility |
| --- | --- |
| `run_engine` | Run lifecycle management, state reconstruction |
| `workflow_engine` | State transition evaluation, gate sequencing |
| `gate_evaluator` | 4-step gate validation (see Section 7) |

### Layer 5 — Domain Components

| Module | Responsibility |
| --- | --- |
| `runtime/artifacts/` | Artifact lifecycle operations |
| `runtime/agents/` | Agent invocation adapter (`AgentAdapter` protocol) |
| `runtime/decisions/` | Decision system; returns typed signals, never writes directly |
| `runtime/events/` | Append-only event system with monotonic counter |
| `runtime/knowledge/` | Static extraction hook registry |

### Layer 6 — CLI (`runtime/cli.py`)

Five commands: `run`, `resume`, `status`, `check`, `advance`.

The `advance` command performs exactly one workflow transition per invocation.
The CLI cannot become an autonomous executor.

---

## 7. Gate Validation

Every state transition in the workflow is protected by a 4-step gate check:

1. **inputs_present** — all declared input artifacts exist in the run directory
2. **artifact_presence** — the required artifact for this gate exists
3. **approval_check** — `decision_log.yaml` contains a matching `approve` entry with
   correct `artifact_id` and `artifact_hash`
4. **condition_check** — the artifact's outcome field matches the required value

If any step fails, the gate blocks. No fallback, no inference, no automatic retry.

Gate behavior on failure: stop, record a `workflow.transition_checked` event with
`blocked: true`, do not advance, do not retry.

---

## 8. Relationship to Contracts

The `contracts/` directory contains the **DevOS kernel rules** — the normative
specification that all runtime implementations must comply with.

| Contract | Purpose |
| --- | --- |
| `contracts/runtime_contract.md` | Primary runtime spec: run identity, artifact layout, gate checks, rework model, events |
| `contracts/system_invariants.md` | Non-negotiable invariants; override forbidden |
| `contracts/framework_validation_contract.md` | 35 self-consistency criteria for system compliance |
| `contracts/framework_versioning_policy.md` | Version scheme and breaking change classification |
| `contracts/migration_contract.md` | Major version migration process |
| `contracts/capability_integration_contract.md` | Rules for project capability integration |
| `contracts/domain_input_contracts.md` | Mandatory project input specifications |
| `contracts/artifact_status_model.md` | Optional lifecycle vocabulary for artifacts |

The framework layer defines the rules. The runtime engine enacts them. Contracts are
loaded once at initialization and are never modified during execution.

---

## 9. Key Design Decisions

Derived from `docs/runtime_module_architecture.md`:

| ID | Decision |
| --- | --- |
| D-01 | The event system is the sole cross-cutting dependency; all other modules are isolated |
| D-02 | Framework loaders are called once at runtime initialization |
| D-03 | The Decision System returns typed signals; it never writes to the decision log directly |
| D-04 | The Artifact System validates structure, not semantics |
| D-05 | The CLI `advance` command performs exactly one transition per invocation |
| D-06 | The `AgentAdapter` protocol isolates the invocation mechanism from the engine |
| D-07 | No in-memory state survives between CLI invocations; state is reconstructed from the filesystem |

---

## Further Reading

- `docs/phase3_runtime_realization_plan.md` — normative engineering specification for the runtime implementation
- `docs/runtime_module_architecture.md` — full Python-style interface signatures for all 8 major modules
- `docs/workflow_state_machine.md` — Mermaid visualization of all three workflow state machines
- `docs/event_model.md` — canonical typed event model with full payload schemas
- `docs/knowledge_query_contract.md` — knowledge layer extraction and query contract
