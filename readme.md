<!--
This repository uses `readme.md` as the primary documentation file.
`README.md` exists for ecosystem compatibility (GitHub, tooling).
-->

# human-governed-ai-framework (Minimal v1)

Primary documentation: `readme.md`

This repository contains the **framework layer only**:

- deterministic, auditable workflows
- role-based single-shot agents
- artifact-only handoffs
- explicit human decisions

For the target structure and philosophy, see: `readme.md`

---

> A deterministic, auditable, human-in-the-loop agent framework for AI-assisted software and data development.
> ⚠️ **Read this before anything else**
>
> This framework is deliberately opinionated.
>
> Before evaluating features, structure, or agents, read the
> **[ANTI_FAQ.md](./ANTI_FAQ.md)**.
>
> It explains what this framework **is not**,  
> which assumptions it **explicitly rejects**,  
> and why certain “obvious” shortcuts are intentionally forbidden.

---

## 🧭 Purpose

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

## 🧠 Core Philosophy

> **Learning without loss of control.**

AI agents are powerful, but unchecked autonomy leads to:

- hidden decisions
- architectural drift
- untraceable changes
- accidental complexity

This framework treats **control, traceability, and explicit decisions as first-class concepts**.

---

## 🚫 What This Framework Is NOT

- ❌ Not an autonomous multi-agent system  
- ❌ Not a self-modifying codebase  
- ❌ Not a domain-specific solution  
- ❌ Not a replacement for human judgment  

---

## ✅ What This Framework IS

- ✅ Deterministic
- ✅ Auditable
- ✅ Role-based
- ✅ Artifact-driven
- ✅ Human-governed
- ✅ Project-independent

---

## 🧱 Fundamental Invariants (Non-Negotiable)

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

➡️ See: `system_invariants.md`

---

## 🧩 Separation of Concerns

| Layer | Responsibility |
| --- | --- |
| **Framework** | Roles, workflows, invariants, artifact types |
| **Project** | Domain knowledge, rules, validation logic |
| **Run** | Concrete execution and produced artifacts |

🚨 **No domain logic in the framework**  
🚨 **No workflow logic in projects**

---

## 📥 Required Project Inputs (Minimal Runnable Set)

A project **must provide the following input artifacts**.  
Without them, the workflow **must not start**.

### 🔴 Mandatory Inputs

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

   Guidance example (non-normative): `examples/architecture_contract.example.md`

⚠️ If any mandatory input is missing:  
`INIT → FAILED`

The framework validates presence only; semantic correctness and validation of domain inputs remain project-owned.

---

## 📘 Recommended Project Inputs (Quality Enhancers)

These inputs are **optional**, but strongly recommended to improve decision quality and reduce ambiguity.

- **`data_model.md`**  

  Key entities, relationships, and semantic expectations.

- **`evaluation_criteria.md`**  

  Defines what “good enough” means beyond automated tests.

- **`goldstandard_knowledge.md`**  

  Reference outputs, known-correct results, or truth sets.

These files **do not alter the workflow**, but significantly improve:

- planning quality
- review precision
- test relevance

---

## 🤖 Agent Model

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

## 🧠 Domain Sub-Agents (Project-Provided)

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

See: `capabilities.yaml`

---

## 📄 Artifacts as Contracts

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

Artifact lifecycle vocabulary (optional guidance): `artifact_status_model.md`

Artifact status (if used) is informational only and never replaces explicit workflow gates or human decisions recorded in decision_log.yaml.

---

## 🏛 Architecture Governance

Architecture is enforced by:

- `agent_architecture_guardian`

Architecture changes are **not errors**, but must occur via:

- `architecture_change_proposal.md`
- versioned contracts (v1 → v2)

---

## 🔁 Workflow Model

### Primary Delivery Cycle (State Machine)

INIT
→ PLANNING
→ ARCH_CHECK
→ TEST_DESIGN
→ BRANCH_READY
→ IMPLEMENTING
→ TESTING
→ REVIEWING
→ ACCEPTED | ACCEPTED_WITH_DEBT | FAILED

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

### Secondary Improvement Cycle (Asynchronous)

OBSERVE
→ REFLECT
→ PROPOSE
→ HUMAN_DECISION
→ (optional) new_change_intent

Visualization (non-normative, derived from YAML): `docs/workflow_state_machine.md`

---

## 🧪 Human-in-the-Loop by Design

Humans:

- approve plans
- accept trade-offs
- decide on debt
- approve architecture changes

All approvals/decisions are recorded explicitly (append-only) in:

- `artifacts/decision_log.yaml` (schema: `artifacts/schemas/decision_log.schema.yaml`)

There is **no automatic override path**.

---

## 🛠 Execution Environment

The framework is intentionally **tool-agnostic**.

Cursor is currently used as:

- working environment
- orchestration surface
- artifact editor

**Understand first → automate later.**

---

## 📁 Repository Structure (Target)

human-governed-ai-framework/
├─ README.md
├─ system_invariants.md
├─ workflow/
│ └─ default_workflow.yaml
├─ agents/
│ └─ *.md
├─ artifacts/
│ └─ schemas/
├─ capabilities.yaml
├─ domain_input_contracts.md
└─ improvement/
└─ improvement_cycle.yaml

---

## 🧠 Guiding Principle

> **The framework defines how work is done.**  
> **Projects define what work is done.**  
> **Agents execute. The orchestrator coordinates. Humans decide.**

---

## 📌 Status

This repository represents the **framework layer only**.  
It is intentionally minimal, explicit, and conservative by design.
