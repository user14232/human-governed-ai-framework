<!--
This repository uses `readme.md` as the primary documentation file.
`README.md` exists for ecosystem compatibility (GitHub, tooling).
-->

# DevOS — Governance Kernel for AI-Assisted Engineering

> **Status:** Experimental / Conceptual — not production-ready.

> **Read this before anything else.**
>
> DevOS is deliberately opinionated.
>
> Before evaluating features, structure, or agents, read
> **[anti_faq.md](./anti_faq.md)**.
>
> It explains what DevOS **is not**,
> which assumptions it **explicitly rejects**,
> and why certain "obvious" shortcuts are intentionally forbidden.

---

## 1. Overview

DevOS is a **governance kernel for AI-assisted software development** that executes artifact-driven workflows.

The system coordinates planning, execution, validation, and review using **deterministic workflow governance**. It enforces explicit state transitions, artifact-based handoffs, and human-approved decisions over every change.

DevOS is explicitly **not** an autonomous system. It provides:

- deterministic workflows with explicit state machines
- agent role contracts with bounded responsibilities
- artifact-based handoffs as the only legal communication channel
- versioned decisions recorded in an append-only log
- human-in-the-loop governance at every architectural gate

**Projects define what work is done. DevOS governs how it is done. Agents execute. The kernel coordinates. Humans decide.**

---

## 2. Development Pipeline

The complete path from idea to governed change:

```
Exploration / planning (external)
         ↓
Intent generation
  → change_intent.yaml
         ↓
DevOS workflow execution (INIT → PLANNING → ARCH_CHECK → TEST_DESIGN
                          → BRANCH_READY → IMPLEMENTING → TESTING → REVIEWING)
         ↓
Run artifacts (implementation_plan, test_design, test_report, review_result)
         ↓
Knowledge extraction (future)
         ↓
Context retrieval for agents (future)
```

Planning is **always external to DevOS**. DevOS does not decide what should be built. It governs how approved, scoped work items progress through a disciplined execution workflow.

See `docs/architecture/development_pipeline.md` for the full pipeline specification.

---

## 3. System Architecture

DevOS consists of four distinct systems with clearly bounded responsibilities:

| System | Role |
| --- | --- |
| **DevOS Kernel** | Deterministic governance core — run lifecycle, workflow execution, gate validation, artifact validation, event logging |
| **Agent Runtime** | AI reasoning execution — agent selection, context building, LLM invocation, artifact production |
| **Capability System** | Tool access for agents — Git, Linear, filesystem, MCP servers, codebase analysis |
| **Knowledge System** | Persistent engineering memory — knowledge extraction, indexing, and deterministic query _(future)_ |

**Only the DevOS Kernel governs workflow execution.** The Agent Runtime, Capability System, and Knowledge System are consumers of the Kernel's contracts — they do not control workflow state.

Additional cross-cutting layers:

| Layer | Role |
| --- | --- |
| **Intent System** | Translates external planning artifacts into `change_intent.yaml` _(future)_ |
| **Planning Layer** | Repository-owned work breakdown management (`capabilities/planning/`) |
| **Context System** | Deterministic context assembly for agent invocations _(future)_ |
| **Framework** | Normative governance definitions loaded by the Kernel |

See `docs/vision/devos_kernel_architecture.md` for the canonical architecture reference.

---

## 4. Repository Structure

```
devos/
│
├─ framework/              # Kernel governance definitions (normative specification)
│   ├─ workflows/          # Delivery and improvement cycle state machines
│   ├─ artifacts/schemas/  # All artifact contracts and schemas
│   ├─ contracts/          # System invariants, runtime contract, capability contracts
│   └─ agents/             # Agent role contracts
│
├─ kernel/                 # Deterministic workflow runtime implementation
│   ├─ engine/             # Run engine, workflow engine, gate evaluator
│   ├─ artifacts/          # Artifact storage and immutability enforcement
│   ├─ decisions/          # Decision log reader
│   ├─ events/             # Typed event system and metrics
│   ├─ knowledge/          # Extraction hooks (future)
│   ├─ store/              # Filesystem abstraction
│   ├─ types/              # Shared value objects
│   └─ cli.py              # Entry point: run, resume, status, check, advance
│
├─ agent_runtime/          # Agent execution layer and LLM adapters
│
├─ capabilities/           # External tool integrations
│   ├─ planning/           # Deterministic planning artifact management
│   └─ linear/             # Linear project sync adapter
│
├─ docs/                   # Architecture, roadmap, and system documentation
│   ├─ vision/             # Canonical architecture and product vision
│   ├─ architecture/       # Integration model, agent contracts, pipeline
│   ├─ framework/          # Event model, workflow model, knowledge contracts
│   ├─ runtime/            # Runtime execution model and module architecture
│   ├─ roadmap/            # Future feature designs (intent, context, knowledge systems)
│   └─ governance/         # Boundaries, non-goals, anti-patterns
│
├─ examples/               # Example inputs, filled templates, and run simulations
│
├─ workspace_examples/     # Example DevOS workspaces
│   ├─ manual_runtime_exploration/
│   └─ runtime_simulation/
│
└─ tests/                  # Unit, integration, and end-to-end tests
```

---

## 5. Core Concepts

DevOS models software delivery as a structured sequence of system primitives:

```
Run → Workflow → Agent → Artifact → Decision → Event → Knowledge
```

| Primitive | Role |
| --- | --- |
| **Run** | Bounded execution of one change intent |
| **Workflow** | State machine that orchestrates a run from INIT to terminal state |
| **Agent** | Single-shot executor invoked by the workflow for one bounded task |
| **Artifact** | Structured output; the only legal communication channel between agents |
| **Decision** | Explicit human authorization recorded append-only in `decision_log.yaml` |
| **Event** | Append-only timeline entry for every system action |
| **Knowledge Record** | Extracted, traceable record derived from run artifacts _(future)_ |

### OS Mental Model

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

Agents do not control execution. The workflow engine governs the process.

### Fundamental Invariants

These rules apply globally and always:

- Agents are **single-shot**, never looping
- Iteration happens **only via the Orchestrator**
- All handoffs occur **exclusively through artifacts**
- Artifacts are versioned, owner-bound, and typically immutable
- Architecture may change, but **only explicitly and versioned**
- Human decisions are **part of the system**
- Improvements create **proposals**, never automatic changes

See `framework/contracts/system_invariants.md`.

---

## 6. Getting Started

### Minimal Development Flow

1. Create `change_intent.yaml` in your project's `.devOS/project_inputs/` directory.
2. Run the DevOS workflow via the kernel CLI:
   ```
   python -m kernel.cli run --intent .devOS/project_inputs/change_intent.yaml
   ```
3. Agents produce artifacts at each workflow stage.
4. The workflow advances through states: `INIT → PLANNING → ARCH_CHECK → ... → ACCEPTED`

### Required Project Inputs

Place these under `<project_root>/.devOS/project_inputs/`:

| File | Purpose |
| --- | --- |
| `change_intent.yaml` | Defines the scoped change to execute |
| `domain_scope.md` | Explicit in-scope and out-of-scope boundaries |
| `domain_rules.md` | Hard domain invariants |
| `source_policy.md` | Source of truth definitions |
| `glossary.md` | Unambiguous terminology |
| `architecture_contract.md` | System boundaries and dependency rules |

Templates: `examples/templates/mandatory/`

If any mandatory input is missing: `INIT → FAILED`.

### Pre-Workflow Planning

The `capabilities/planning/` package manages the repository-owned work breakdown artifact before workflow execution:

```bash
python -m capabilities.planning.cli validate .devOS/planning/project_plan.yaml --lint-mode enforce
```

---

## Agent Model

Agents are **roles**, not persistent entities. Each agent:

- has a single, bounded responsibility
- consumes defined input artifacts
- produces defined output artifacts
- has explicit prohibitions

### Core Roles

- `agent_orchestrator` — coordinates run progression
- `agent_planner` — produces `implementation_plan.yaml`
- `agent_architecture_guardian` — validates architecture compliance
- `agent_test_designer` — produces `test_design.yaml`
- `agent_test_author` — writes test code
- `agent_test_runner` — executes tests and produces `test_report.json`
- `agent_branch_manager` — manages branch lifecycle
- `agent_implementer` — produces implementation
- `agent_reviewer` — produces `review_result.md`
- `agent_release_manager` — manages release lifecycle

Role contracts: `framework/agents/`

---

## Workflow Model

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

### Improvement Cycle (Asynchronous)

```
OBSERVE → REFLECT → PROPOSE → HUMAN_DECISION → (optional) new_change_intent
```

Workflow definitions: `framework/workflows/`

---

## Human-in-the-Loop

All human approvals and decisions are recorded explicitly in:

```
runs/<run_id>/decision_log.yaml
```

There is no automatic override path. Humans approve plans, accept trade-offs, decide on debt, and authorize architecture changes.

Schema: `framework/artifacts/schemas/decision_log.schema.yaml`

---

## Key References

| Document | Purpose |
| --- | --- |
| `docs/vision/devos_kernel_architecture.md` | Canonical four-system architecture reference |
| `docs/architecture/development_pipeline.md` | Full planning-to-execution pipeline |
| `framework/contracts/runtime_contract.md` | Normative runtime execution contract |
| `framework/contracts/system_invariants.md` | Non-negotiable system invariants |
| `docs/architecture/agent_contracts.md` | Agent contract model and integration |
| `docs/framework/event_model.md` | Canonical typed event model |
| `docs/framework/knowledge_query_contract.md` | Knowledge layer contract |
| `docs/roadmap/` | Future feature designs |

---

## Change Log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Initial framework and runtime specification. |
| v1.1 | 2026-03-14 | Architecture alignment refactor. Added System Overview and OS Mental Model. |
| v1.2 | 2026-03-14 | Added Planning Layer documentation with deterministic input/output contracts. |
| v1.3 | 2026-03-15 | Defined canonical project inputs namespace `.devOS/project_inputs/`. |
| v1.4 | 2026-03-15 | Restructured README to reflect four-system architecture and actual repository layout. |
