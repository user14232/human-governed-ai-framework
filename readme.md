<!--
This repository uses `readme.md` as the primary documentation file.
`README.md` exists for ecosystem compatibility (GitHub, tooling).
-->

# DevOS — Deterministic Runtime for AI-Assisted Engineering

> Deterministic runtime for AI-assisted engineering.

**Status:** Experimental / Conceptual — not production-ready.

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

## Purpose

DevOS is a **deterministic runtime for AI-assisted engineering workflows**.

It is a personal, project-agnostic system for building software and data systems
with AI assistance without losing engineering control.

DevOS is explicitly **not** an autonomous system.

It provides:

- deterministic workflows
- explicit agent roles
- artifact-based handoffs
- versioned decisions
- human-in-the-loop governance
- continuous improvement **via explicit, human-approved proposals**

**Projects provide domain knowledge.
DevOS provides process, structure, and control.**

---

## Core Philosophy

> **Learning without loss of control.**

AI agents are powerful, but unchecked autonomy leads to:

- hidden decisions
- architectural drift
- untraceable changes
- accidental complexity

DevOS treats **control, traceability, and explicit decisions as first-class system properties**.

---

## What DevOS Is NOT

- Not an autonomous multi-agent system
- Not a self-modifying codebase
- Not a domain-specific solution
- Not a replacement for human judgment

---

## What DevOS IS

- Deterministic
- Auditable
- Role-based
- Artifact-driven
- Human-governed
- Project-independent

---

## System Overview

DevOS models software delivery as a structured sequence of system primitives:

```
Run → Workflow → Agent → Artifact → Decision → Event → Knowledge
```

| Primitive | Role |
| --- | --- |
| **Run** | Bounded execution of one change intent |
| **Workflow** | State machine that orchestrates a run |
| **Agent** | Single-shot executor invoked by the workflow |
| **Artifact** | Structured output; the only channel between agents |
| **Decision** | Explicit human authorization recorded in `decision_log.yaml` |
| **Event** | Append-only timeline entry for every system action |
| **Knowledge** | Extracted, traceable records derived from artifacts |

### Engineering OS Mental Model

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

---

## Fundamental Invariants (Non-Negotiable)

These rules apply **globally and always**:

- Agents are **single-shot**, never looping
- Iteration happens **only via the Orchestrator**
- All handoffs occur **exclusively through artifacts**
- Artifacts are:
  - versioned
  - owner-bound
  - typically immutable
- Architecture may change, but **only explicitly and versioned**
- Human decisions are **part of the system**
- Improvements create **proposals**, never automatic changes

See: `framework/contracts/system_invariants.md`

---

## Separation of Concerns

| Layer | Responsibility |
| --- | --- |
| **Framework** | Roles, workflows, invariants, artifact types (DevOS kernel rules) |
| **Project** | Domain knowledge, rules, validation logic |
| **Run** | Concrete execution and produced artifacts |

**No domain logic in the framework layer.
No workflow logic in projects.**

---

## Required Project Inputs (Minimal Runnable Set)

A project **must provide the following input artifacts**.
Without them, the workflow **must not start**.

### Canonical Location

Place mandatory inputs under:

```
<project_root>/.devOS/project_inputs/
```

The runtime resolves this directory automatically. If `.devOS/project_inputs/` exists, it is used.
If not, the project root is used as a legacy fallback (migration aid only).
Use `--project-inputs-root` on the CLI to override explicitly.

Templates: `examples/templates/mandatory/` — copy to `.devOS/project_inputs/` and fill in.

### Mandatory Inputs

1. **`domain_scope.md`**

   Defines what is explicitly **in scope** and **out of scope**.

1. **`domain_rules.md`**

   Hard domain invariants that must never be violated.

1. **`source_policy.md`**

   Defines which sources are considered truth, including priorities and conflict rules.

1. **`glossary.md`**

   Ensures semantic clarity and unambiguous terminology.

1. **`architecture_contract.md`**

   Explicit architecture contract defining:

   - system boundaries
   - layers and dependency direction
   - allowed / forbidden patterns
   - stability guarantees

   Guidance example (non-normative): `examples/filled/architecture_contract.example.md`

If any mandatory input is missing: `INIT → FAILED`

DevOS validates presence only; semantic correctness and validation of domain inputs remain project-owned.

---

## Recommended Project Inputs (Quality Enhancers)

These inputs are **optional**, but strongly recommended to improve decision quality and reduce ambiguity.

- **`data_model.md`**

  Key entities, relationships, and semantic expectations.

- **`evaluation_criteria.md`**

  Defines what "good enough" means beyond automated tests.

- **`goldstandard_knowledge.md`**

  Reference outputs, known-correct results, or truth sets.

These files **do not alter the workflow**, but significantly improve:

- planning quality
- review precision
- test relevance

---

## Agent Model

Agents are **roles**, not persistent entities.
They are deliberately **non-autonomous executors**:

- they do not infer intent
- they do not optimize plans
- they do not advance workflows
- they do not make decisions

Each agent:

- has a single responsibility
- consumes defined artifacts
- produces defined artifacts
- has explicit prohibitions

### Core Roles

- `agent_orchestrator`
- `agent_planner`
- `agent_architecture_guardian`
- `agent_test_designer`
- `agent_test_author`
- `agent_test_runner`
- `agent_branch_manager`
- `agent_implementer`
- `agent_reviewer`
- `agent_release_manager`

### System Actor (Meta-Role)

- `human_decision_authority`

### Improvement Cycle Roles

- `agent_reflector`
- `agent_improvement_designer`

Each role is defined as a standalone contract in `framework/agents/`.

---

## Domain Sub-Agents (Project-Provided)

Projects may provide **domain-specific capability agents**.

They may:

- explain rules
- validate outputs
- define constraints

They may **not**:

- plan
- decide
- write implementation code
- alter workflows

DevOS defines **capability interfaces only**, e.g.:

- `domain_validation`
- `domain_explanation`

See: `framework/contracts/capabilities.yaml`

---

## Artifacts as Contracts

Every artifact defines:

- owner
- purpose
- write policy
- allowed readers

Artifacts are the **only legal communication channel** between agents.

Key artifacts include:

- `change_intent.yaml`
- `implementation_plan.yaml`
- `test_design.yaml`
- `test_report.json`
- `review_result.md`
- `design_tradeoffs.md`
- `run_metrics.json`
- `decision_log.yaml` (approval/decision record)

Schemas live under: `framework/artifacts/schemas/`

Artifact lifecycle vocabulary (optional guidance): `framework/contracts/artifact_status_model.md`

Artifact status (if used) is informational only and never replaces explicit workflow gates or human decisions recorded in `decision_log.yaml`.

---

## Architecture Governance

Architecture is enforced by:

- `agent_architecture_guardian`

Architecture changes are **not errors**, but must occur via:

- `architecture_change_proposal.md`
- versioned contracts (v1 → v2)

---

## Workflow Model

### Primary Delivery Cycle (State Machine)

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

Visualization (non-normative, derived from YAML): `docs/framework/workflow_state_machine.md`

### Secondary Improvement Cycle (Asynchronous)

```
OBSERVE
→ REFLECT
→ PROPOSE
→ HUMAN_DECISION
→ (optional) new_change_intent
```

Visualization (non-normative, derived from YAML): `docs/framework/workflow_state_machine.md`

---

## Human-in-the-Loop by Design

Humans:

- approve plans
- accept trade-offs
- decide on debt
- approve architecture changes

All approvals/decisions are recorded explicitly (append-only) in:

- `runs/<run_id>/decision_log.yaml` (schema: `framework/artifacts/schemas/decision_log.schema.yaml`)

The file `examples/filled/decision_log.example.yaml` in this repository is an example only.
The normative per-run location is `runs/<run_id>/decision_log.yaml`
(see `framework/contracts/runtime_contract.md` Section 2.3).

There is **no automatic override path**.

---

## Execution Environment

DevOS is intentionally **tool-agnostic**.

Cursor is currently used as:

- working environment
- orchestration surface
- artifact editor

**Understand first → automate later.**

---

## Planning Layer (Pre-Workflow)

DevOS also includes a deterministic planning package for repository-owned work breakdowns:

- package: `integrations/planning/`
- canonical artifact: `.devOS/planning/project_plan.yaml`
- compatibility fallback: `.devos/planning/project_plan.yaml`
- gate behavior: parse + lint before any optional external sync

This layer is upstream of delivery workflow execution and produces validated planning
inputs that can be projected to external systems (for example Linear) without making
those systems the source of truth.

---

## Repository Structure

The repository is organized into five conceptual layers:

```
devos/
│
│  Root
├─ readme.md                              # Primary documentation (start here)
├─ anti_faq.md                            # Read before evaluating DevOS
│
│  Framework (DevOS normative specification)
├─ framework/
│   ├─ docs/
│   │   ├─ DEV_OS_product_vision.md       # DevOS product vision
│   │   ├─ devos_architecture.md          # System architecture reference
│   │   ├─ workflow_state_machine.md      # State machine visualization (non-normative)
│   │   └─ governance/
│   │       └─ anti_patterns_and_non-goals.md
│   │
│   ├─ contracts/
│   │   ├─ README.md                      # Navigation guide for runtime implementers
│   │   ├─ runtime_contract.md            # Primary runtime spec
│   │   ├─ system_invariants.md           # Non-negotiable invariants
│   │   ├─ framework_validation_contract.md
│   │   ├─ framework_versioning_policy.md
│   │   ├─ migration_contract.md
│   │   ├─ capability_integration_contract.md
│   │   ├─ domain_input_contracts.md
│   │   ├─ capabilities.yaml
│   │   └─ artifact_status_model.md
│   │
│   ├─ workflows/
│   │   ├─ default_workflow.yaml          # Delivery state machine (INIT → terminal)
│   │   ├─ release_workflow.yaml          # Release lifecycle (opt-in)
│   │   └─ improvement_cycle.yaml         # Improvement cycle (OBSERVE → HUMAN_DECISION)
│   │
│   ├─ agents/
│   │   ├─ agent_orchestrator.md
│   │   ├─ agent_planner.md
│   │   └─ ... (all agent contracts)
│   │
│   └─ artifacts/
│       └─ schemas/                       # All artifact contracts (schemas)
│           ├─ *.schema.yaml
│           ├─ *.schema.json
│           └─ *.schema.md
│
│  Runtime (execution engine implementation)
├─ runtime/
│   ├─ cli.py
│   ├─ engine/
│   ├─ events/
│   ├─ store/
│   ├─ agents/
│   ├─ artifacts/
│   ├─ decisions/
│   ├─ framework/
│   ├─ knowledge/
│   └─ types/
│
│  Integrations (connectors)
├─ integrations/
│   ├─ linear/                            # Linear project creator
│   └─ planning/                          # Deterministic planning package (pre-workflow)
│       ├─ cli.py
│       ├─ planning_engine.py
│       ├─ planning_parser.py
│       ├─ planning_models.py
│       ├─ work_item_linter.py
│       └─ work_item_provider.py
│
│  Layer 5 — Observability & Knowledge
│  (docs/framework/event_model.md, docs/framework/knowledge_query_contract.md)
│
│  Examples (DevOS workspaces)
└─ examples/
    ├─ filled/
    │   ├─ architecture_contract.example.md
    │   ├─ decision_log.example.yaml
    │   └─ run_example/
    ├─ templates/
    │   ├─ mandatory/                     # Project input templates (must provide)
    │   └─ optional/                      # Project input templates (optional)
    └─ workspaces/
        ├─ manual_runtime_exploration/    # Manual exploration workspace
        └─ runtime_simulation_workspace/  # Simulation workspace (with runs/)
```

---

## Guiding Principle

> **DevOS defines how work is done.**
> **Projects define what work is done.**
> **Agents execute. The orchestrator coordinates. Humans decide.**

---

## v1 Scope

The following components are **fully normative and implemented in v1**:

| Component | Status |
| --- | --- |
| Delivery workflow (`INIT` → `REVIEWING` → terminal) | v1 normative |
| `agent_orchestrator`, `agent_planner`, `agent_architecture_guardian` | v1 normative |
| `agent_test_designer`, `agent_test_author`, `agent_test_runner` | v1 normative |
| `agent_branch_manager`, `agent_implementer`, `agent_reviewer` | v1 normative |
| `human_decision_authority` | v1 normative |
| Improvement cycle | v1 normative |
| `agent_reflector`, `agent_improvement_designer` | v1 normative |
| `framework/contracts/runtime_contract.md` | v1 normative |

The following components were **added in v1.1** (all now normative):

| Component | Status |
| --- | --- |
| Release workflow (`framework/workflows/release_workflow.yaml`) | v1.1 normative |
| Event model (`docs/framework/event_model.md`, `framework/artifacts/schemas/event_envelope.schema.json`) | v1.1 normative |
| Knowledge layer (`knowledge_record`, `knowledge_index`, `docs/framework/knowledge_query_contract.md`) | v1.1 normative |
| Capability integration contract (`framework/contracts/capability_integration_contract.md`, `capability_registry.schema.yaml`) | v1.1 normative |
| Versioning policy (`framework/contracts/framework_versioning_policy.md`) | v1.1 normative |
| Migration contract (`framework/contracts/migration_contract.md`, `migration_record.schema.yaml`) | v1.1 normative |
| System self-validation (`framework/contracts/framework_validation_contract.md`) | v1.1 normative |

---

## Status

This repository represents the **framework layer (DevOS kernel rules)** and the **DevOS system architecture**.
It is intentionally minimal, explicit, and conservative by design.

See `framework/contracts/runtime_contract.md` for the normative runtime execution contract.

Key normative references:
- `framework/contracts/runtime_contract.md` — run lifecycle, gate checks, invocation, rework, events
- `docs/framework/event_model.md` — canonical typed event model
- `docs/framework/knowledge_query_contract.md` — knowledge layer contract
- `framework/contracts/framework_validation_contract.md` — system self-consistency criteria
- `framework/contracts/framework_versioning_policy.md` — version evolution and breaking change policy
- `framework/contracts/migration_contract.md` — major version migration process
- `framework/contracts/capability_integration_contract.md` — project capability integration rules

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Corrected decision_log.yaml location reference to point to per-run normative path. Updated repository structure and v1.1 component status. Added key normative references section. |
| v1.1 | 2026-03-14 | Architecture alignment refactor. Re-titled as DevOS. Added System Overview and OS Mental Model sections. Updated repository structure to reflect documentation layers. |
| v1.2 | 2026-03-14 | Added explicit Planning Layer documentation (`integrations/planning`) with deterministic input/output contracts and canonical `.devOS` artifact path. |
| v1.3 | 2026-03-15 | Defined canonical project inputs namespace `.devOS/project_inputs/` with explicit resolution fallback chain. Updated CLI and runtime contract accordingly. |
