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

See: `contracts/system_invariants.md`

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

Each role is defined as a standalone contract in `/agents`.

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

See: `contracts/capabilities.yaml`

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

Schemas live under: `artifacts/schemas/`

Artifact lifecycle vocabulary (optional guidance): `contracts/artifact_status_model.md`

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

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

### Secondary Improvement Cycle (Asynchronous)

```
OBSERVE
→ REFLECT
→ PROPOSE
→ HUMAN_DECISION
→ (optional) new_change_intent
```

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

---

## Human-in-the-Loop by Design

Humans:

- approve plans
- accept trade-offs
- decide on debt
- approve architecture changes

All approvals/decisions are recorded explicitly (append-only) in:

- `runs/<run_id>/decision_log.yaml` (schema: `artifacts/schemas/decision_log.schema.yaml`)

The file `examples/filled/decision_log.example.yaml` in this repository is an example only.
The normative per-run location is `runs/<run_id>/decision_log.yaml`
(see `contracts/runtime_contract.md` Section 2.3).

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

## Repository Structure

The repository is organized into five conceptual layers:

```
human-governed-ai-framework/
│
│  Layer 1 — Vision
├─ readme.md                              # Primary documentation (start here)
├─ anti_faq.md                            # Read before evaluating DevOS
│
│  Layer 2 — Architecture
├─ docs/
│   ├─ DEV_OS_product_vision.md           # DevOS product vision
│   ├─ devos_architecture.md              # System architecture reference
│   ├─ workflow_state_machine.md          # State machine visualization (non-normative)
│   ├─ v1_readiness_assessment.md         # Readiness assessment
│   └─ governance/
│       └─ anti_patterns_and_non-goals.md # Anti-patterns, failure modes, non-goals
│
│  Layer 3 — Contracts (DevOS Kernel Rules)
├─ contracts/
│   ├─ README.md                          # Navigation guide for runtime implementers
│   ├─ runtime_contract.md                # Primary runtime spec (run lifecycle, gates, events)
│   ├─ system_invariants.md               # Non-negotiable invariants
│   ├─ framework_validation_contract.md   # 35 self-consistency criteria
│   ├─ framework_versioning_policy.md     # Version scheme and change classification
│   ├─ migration_contract.md              # Major version migration process
│   ├─ capability_integration_contract.md # How project capabilities integrate
│   ├─ domain_input_contracts.md          # Required project inputs contract
│   ├─ capabilities.yaml                  # Capability interface definitions
│   └─ artifact_status_model.md           # Optional lifecycle vocabulary for artifacts
│
│  Layer 4 — System Primitives
├─ workflow/
│   ├─ default_workflow.yaml              # Delivery state machine (INIT → terminal)
│   ├─ release_workflow.yaml              # Release lifecycle (opt-in)
│   └─ improvement_cycle.yaml             # Improvement cycle (OBSERVE → HUMAN_DECISION)
│
├─ agents/
│   ├─ agent_orchestrator.md
│   ├─ agent_planner.md
│   ├─ agent_architecture_guardian.md
│   ├─ agent_test_designer.md
│   ├─ agent_test_author.md
│   ├─ agent_test_runner.md
│   ├─ agent_branch_manager.md
│   ├─ agent_implementer.md
│   ├─ agent_reviewer.md
│   ├─ agent_release_manager.md
│   ├─ agent_reflector.md
│   ├─ agent_improvement_designer.md
│   └─ human_decision_authority.md
│
├─ artifacts/
│   └─ schemas/                           # All artifact contracts (schemas)
│       ├─ *.schema.yaml
│       ├─ *.schema.json
│       └─ *.schema.md
│
│  Layer 5 — Observability & Knowledge
│  (docs/event_model.md, docs/knowledge_query_contract.md)
│
│  Examples
└─ examples/
    ├─ filled/
    │   ├─ architecture_contract.example.md
    │   ├─ decision_log.example.yaml       # Example only; normative: runs/<run_id>/decision_log.yaml
    │   └─ run_example/                   # Complete end-to-end delivery run example
    └─ templates/
        ├─ mandatory/                     # Project input templates (must provide)
        └─ optional/                      # Project input templates (optional)
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
| `contracts/runtime_contract.md` | v1 normative |

The following components were **added in v1.1** (all now normative):

| Component | Status |
| --- | --- |
| Release workflow (`workflow/release_workflow.yaml`) | v1.1 normative |
| Event model (`docs/event_model.md`, `artifacts/schemas/event_envelope.schema.json`) | v1.1 normative |
| Knowledge layer (`knowledge_record`, `knowledge_index`, `docs/knowledge_query_contract.md`) | v1.1 normative |
| Capability integration contract (`contracts/capability_integration_contract.md`, `capability_registry.schema.yaml`) | v1.1 normative |
| Versioning policy (`contracts/framework_versioning_policy.md`) | v1.1 normative |
| Migration contract (`contracts/migration_contract.md`, `migration_record.schema.yaml`) | v1.1 normative |
| System self-validation (`contracts/framework_validation_contract.md`) | v1.1 normative |

---

## Status

This repository represents the **framework layer (DevOS kernel rules)** and the **DevOS system architecture**.
It is intentionally minimal, explicit, and conservative by design.

See `contracts/runtime_contract.md` for the normative runtime execution contract.

Key normative references:
- `contracts/runtime_contract.md` — run lifecycle, gate checks, invocation, rework, events
- `docs/event_model.md` — canonical typed event model
- `docs/knowledge_query_contract.md` — knowledge layer contract
- `contracts/framework_validation_contract.md` — system self-consistency criteria
- `contracts/framework_versioning_policy.md` — version evolution and breaking change policy
- `contracts/migration_contract.md` — major version migration process
- `contracts/capability_integration_contract.md` — project capability integration rules

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Corrected decision_log.yaml location reference to point to per-run normative path. Updated repository structure and v1.1 component status. Added key normative references section. |
| v1.1 | 2026-03-14 | Architecture alignment refactor. Re-titled as DevOS. Added System Overview and OS Mental Model sections. Updated repository structure to reflect documentation layers. |
