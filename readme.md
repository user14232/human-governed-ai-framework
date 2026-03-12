<!--
This repository uses `readme.md` as the primary documentation file.
`README.md` exists for ecosystem compatibility (GitHub, tooling).
-->

# human-governed-ai-framework (Minimal v1)

âš ï¸ Status: Experimental / Conceptual Framework

This repository represents a framework-level exploration.
APIs, roles, and artifacts MAY change.
Not production-ready. Not stable.

Primary documentation: `readme.md`

This repository contains the **framework layer only**:

- deterministic, auditable workflows
- role-based single-shot agents
- artifact-only handoffs
- explicit human decisions

For the target structure and philosophy, see: `readme.md`

---

> A deterministic, auditable, human-in-the-loop agent framework for AI-assisted software and data development.
> âš ï¸ **Read this before anything else**
>
> This framework is deliberately opinionated.
>
> Before evaluating features, structure, or agents, read the
> **[ANTI_FAQ.md](./ANTI_FAQ.md)**.
>
> It explains what this framework **is not**,  
> which assumptions it **explicitly rejects**,  
> and why certain â€œobviousâ€ shortcuts are intentionally forbidden.

---

## ðŸ§­ Purpose

The **Human-Governed AI Framework** is a **personal, project-agnostic framework** for building
software and data systems with AI assistance **without losing control**.

It is explicitly **not** an autonomous system.

Instead, it provides:

- deterministic workflows  
- explicit agent roles  
- artifact-based handoffs  
- versioned decisions  
- human-in-the-loop governance  
- continuous improvement **via explicit, human-approved proposals**

**Projects provide domain knowledge.  
The framework provides process, structure, and control.**

---

## ðŸ§  Core Philosophy

> **Learning without loss of control.**

AI agents are powerful, but unchecked autonomy leads to:

- hidden decisions
- architectural drift
- untraceable changes
- accidental complexity

This framework treats **control, traceability, and explicit decisions as first-class concepts**.

---

## ðŸš« What This Framework Is NOT

- âŒ Not an autonomous multi-agent system  
- âŒ Not a self-modifying codebase  
- âŒ Not a domain-specific solution  
- âŒ Not a replacement for human judgment  

---

## âœ… What This Framework IS

- âœ… Deterministic
- âœ… Auditable
- âœ… Role-based
- âœ… Artifact-driven
- âœ… Human-governed
- âœ… Project-independent

---

## ðŸ§± Fundamental Invariants (Non-Negotiable)

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

âž¡ï¸ See: `contracts/system_invariants.md`

---

## ðŸ§© Separation of Concerns

| Layer | Responsibility |
| --- | --- |
| **Framework** | Roles, workflows, invariants, artifact types |
| **Project** | Domain knowledge, rules, validation logic |
| **Run** | Concrete execution and produced artifacts |

ðŸš¨ **No domain logic in the framework**  
ðŸš¨ **No workflow logic in projects**

---

## ðŸ“¥ Required Project Inputs (Minimal Runnable Set)

A project **must provide the following input artifacts**.  
Without them, the workflow **must not start**.

### ðŸ”´ Mandatory Inputs

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
   - layers & dependency direction
   - allowed / forbidden patterns
   - stability guarantees

   Guidance example (non-normative): `examples/filled/architecture_contract.example.md`

âš ï¸ If any mandatory input is missing:  
`INIT â†’ FAILED`

The framework validates presence only; semantic correctness and validation of domain inputs remain project-owned.

---

## ðŸ“˜ Recommended Project Inputs (Quality Enhancers)

These inputs are **optional**, but strongly recommended to improve decision quality and reduce ambiguity.

- **`data_model.md`**  

  Key entities, relationships, and semantic expectations.

- **`evaluation_criteria.md`**  

  Defines what â€œgood enoughâ€ means beyond automated tests.

- **`goldstandard_knowledge.md`**  

  Reference outputs, known-correct results, or truth sets.

These files **do not alter the workflow**, but significantly improve:

- planning quality
- review precision
- test relevance

---

## ðŸ¤– Agent Model

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

### Core Roles (Framework)

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

### System actor (meta-role)

- `human_decision_authority`

### Improvement Cycle Roles

- `agent_reflector`
- `agent_improvement_designer`

Each role is defined as a standalone contract in `/agents`.

---

## ðŸ§  Domain Sub-Agents (Project-Provided)

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

The framework defines **capability interfaces only**, e.g.:

- `domain_validation`
- `domain_explanation`

See: `contracts/capabilities.yaml`

---

## ðŸ“„ Artifacts as Contracts

Every artifact defines:

- owner
- purpose
- write policy
- allowed readers

Artifacts are the **only legal communication channel** between agents.

Key framework artifacts include:

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

Artifact status (if used) is informational only and never replaces explicit workflow gates or human decisions recorded in decision_log.yaml.

---

## ðŸ› Architecture Governance

Architecture is enforced by:

- `agent_architecture_guardian`

Architecture changes are **not errors**, but must occur via:

- `architecture_change_proposal.md`
- versioned contracts (v1 â†’ v2)

---

## ðŸ” Workflow Model

### Primary Delivery Cycle (State Machine)

INIT
â†’ PLANNING
â†’ ARCH_CHECK
â†’ TEST_DESIGN
â†’ BRANCH_READY
â†’ IMPLEMENTING
â†’ TESTING
â†’ REVIEWING
â†’ ACCEPTED | ACCEPTED_WITH_DEBT | FAILED

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

### Secondary Improvement Cycle (Asynchronous)

OBSERVE
â†’ REFLECT
â†’ PROPOSE
â†’ HUMAN_DECISION
â†’ (optional) new_change_intent

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

---

## ðŸ§ª Human-in-the-Loop by Design

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

## ðŸ›  Execution Environment

The framework is intentionally **tool-agnostic**.

Cursor is currently used as:

- working environment
- orchestration surface
- artifact editor

**Understand first â†’ automate later.**

---

## 📁 Repository Structure

```
human-governed-ai-framework/
├─ readme.md                              # Primary documentation (start here)
├─ anti_faq.md                            # Read before evaluating the framework
│
├─ contracts/                             # All normative framework specifications
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
├─ docs/
│   ├─ event_model.md                     # Typed event model
│   ├─ knowledge_query_contract.md        # Knowledge layer contract
│   ├─ workflow_state_machine.md          # State machine visualization (non-normative)
│   ├─ v1_readiness_assessment.md         # Framework readiness assessment
│   ├─ DEV_OS_product_vision.md           # Product vision background
│   └─ governance/
│       └─ anti_patterns_and_non-goals.md
│
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

## ðŸ§  Guiding Principle

> **The framework defines how work is done.**  
> **Projects define what work is done.**  
> **Agents execute. The orchestrator coordinates. Humans decide.**

---

## ðŸ—‚ v1 Scope

The following components are **fully normative and implemented in v1**:

| Component | Status |
| --- | --- |
| Delivery workflow (`INIT` â†’ `REVIEWING` â†’ terminal) | âœ… v1 normative |
| `agent_orchestrator`, `agent_planner`, `agent_architecture_guardian` | âœ… v1 normative |
| `agent_test_designer`, `agent_test_author`, `agent_test_runner` | âœ… v1 normative |
| `agent_branch_manager`, `agent_implementer`, `agent_reviewer` | âœ… v1 normative |
| `human_decision_authority` | âœ… v1 normative |
| Improvement cycle | âœ… v1 normative |
| `agent_reflector`, `agent_improvement_designer` | âœ… v1 normative |
| `contracts/runtime_contract.md` | âœ… v1 normative |

The following components were **added in v1.1** (all now normative):

| Component | Status |
| --- | --- |
| Release workflow (`workflow/release_workflow.yaml`) | âœ… v1.1 normative |
| Event model (`docs/event_model.md`, `artifacts/schemas/event_envelope.schema.json`) | âœ… v1.1 normative |
| Knowledge layer (`knowledge_record`, `knowledge_index`, `docs/knowledge_query_contract.md`) | âœ… v1.1 normative |
| Capability integration contract (`contracts/capability_integration_contract.md`, `capability_registry.schema.yaml`) | âœ… v1.1 normative |
| Framework versioning policy (`contracts/framework_versioning_policy.md`) | âœ… v1.1 normative |
| Migration contract (`contracts/migration_contract.md`, `migration_record.schema.yaml`) | âœ… v1.1 normative |
| Framework self-validation (`contracts/framework_validation_contract.md`) | âœ… v1.1 normative |

---

## ðŸ“Œ Status

This repository represents the **framework layer only**.  
It is intentionally minimal, explicit, and conservative by design.

See `contracts/runtime_contract.md` for the normative runtime execution contract.

Key normative references:
- `contracts/runtime_contract.md` â€” run lifecycle, gate checks, invocation, rework, events
- `docs/event_model.md` â€” canonical typed event model
- `docs/knowledge_query_contract.md` â€” knowledge layer contract
- `contracts/framework_validation_contract.md` â€” framework self-consistency criteria
- `contracts/framework_versioning_policy.md` â€” version evolution and breaking change policy
- `contracts/migration_contract.md` â€” major version migration process
- `contracts/capability_integration_contract.md` â€” project capability integration rules

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-03-12 | Corrected decision_log.yaml location reference to point to per-run normative path. Updated repository structure and v1.1 component status. Added key normative references section. |
