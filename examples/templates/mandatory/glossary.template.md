# glossary.md

**Status:** REQUIRED PROJECT INPUT (mandatory)  
**Scope:** Project-provided, framework-governed input  
**Audience:** Humans, all framework agents

---

## 1. Purpose

This document defines **authoritative terminology** for this project and its framework.

Its purpose is to:

- prevent semantic ambiguity
- avoid overloaded or intuitive interpretations
- ensure deterministic communication between humans and agents

If a term is defined here, its meaning **must not be reinterpreted elsewhere**.

---

## 2. Core Terms

### Agent

**Definition**  
An *agent* is a **single-shot executor** that performs exactly one well-defined role
by consuming explicit input artifacts and producing explicit output artifacts.

Agents:

- are stateless
- do not loop
- do not retain memory across runs
- do not communicate directly with other agents

#### Forbidden interpretations (Agent)

- autonomous actor  
- persistent entity  
- reasoning system with implicit state

---

### Rolle (Role)

**Definition**  
A *role* is a **contractual responsibility definition** that specifies:

- what an agent may read
- what an agent may write
- what an agent must not do

A role exists independently of any concrete agent execution.

#### Forbidden interpretations (Rolle / Role)

- job title  
- permission set without responsibility  
- dynamic capability assignment

---

### Artefakt (Artifact)

**Definition**  
An *artifact* is a **versioned, explicit, inspectable document** that serves as the
**only legal communication channel** between roles and agents.

Artifacts are:

- owner-bound
- deterministic
- auditable
- typically immutable

#### Forbidden interpretations (Artefakt / Artifact)

- transient messages  
- internal memory  
- undocumented side effects

---

### Entscheidung (Decision)

**Definition**  
A *decision* is an **explicit human approval, rejection, or deferral**
recorded as an append-only entry in a decision artifact.

Decisions:

- are first-class system inputs
- gate workflow transitions
- cannot be inferred or implied

#### Forbidden interpretations (Entscheidung / Decision)

- implicit consent  
- agent-made judgment  
- approval by absence of objection

---

### Review

**Definition**  
A *review* is a **structured evaluation** of produced artifacts against:

- approved plans
- architecture contracts
- domain rules
- test evidence

A review produces an explicit outcome artifact.

#### Forbidden interpretations (Review)

- informal feedback  
- code inspection without recorded outcome  
- subjective opinion

---

### Akzeptanz (Acceptance)

**Definition**  
*Acceptance* is a **formal state** in which a reviewed change is declared
acceptable according to defined criteria and recorded evidence.

Acceptance:

- does not imply perfection
- may include explicitly accepted debt
- must be traceable to a review artifact

#### Forbidden interpretations (Akzeptanz / Acceptance)

- absence of objections  
- emotional agreement  
- implicit approval

---

### Orchestrator

**Definition**  
The *orchestrator* is a **control role** that:

- enforces the workflow state machine
- validates artifact presence
- dispatches exactly one next role per step
- stops execution on failed gates

The orchestrator:

- does not make domain decisions
- does not create plans
- does not modify domain content

#### Forbidden interpretations (Orchestrator)

- manager  
- planner  
- autonomous coordinator

---

### Workflow

**Definition**  
A *workflow* is a **deterministic state machine** that defines:

- allowed states
- valid transitions
- required artifacts and approvals per transition

Workflows are explicit, versioned, and non-interpreted.

#### Forbidden interpretations (Workflow)

- informal process description  
- best-practice guideline  
- adaptive or heuristic flow

---

### Invariante (Invariant)

**Definition**  
An *invariant* is a **non-negotiable rule** that must hold across all executions,
roles, workflows, and artifacts.

Invariants:

- are global or explicitly scoped
- cannot be overridden
- can only be changed via explicit, versioned governance

#### Forbidden interpretations (Invariante / Invariant)

- guideline  
- recommendation  
- convention

---

## 3. Additional Essential Terms

### Domain Rule

**Definition**  
A *domain rule* is a **hard, testable constraint** derived from the problem domain
that must never be violated.

Domain rules:

- use normative language (MUST / MUST NOT)
- are atomic
- are stable and versioned

#### Forbidden interpretations (Domain Rule)

- heuristic  
- design preference  
- quality goal

---

### Architecture Contract

**Definition**  
An *architecture contract* is an explicit agreement defining:

- system boundaries
- layering and dependency direction
- allowed and forbidden patterns
- stability guarantees

It governs structure, not behavior.

---

### Plan (Implementation Plan)

**Definition**  
A *plan* is a **deterministic, stepwise description** of how an approved intent
will be implemented under given constraints.

Plans:

- do not invent requirements
- make assumptions explicit
- are subject to human approval

---

### Change Intent

**Definition**  
A *change intent* captures the **human-approved motivation and scope**
of a change without embedding implementation details.

It defines *why* something should change, not *how*.

---

### Test Evidence

**Definition**  
*Test evidence* consists of **recorded, reproducible test results**
used to evaluate correctness and compliance.

Test evidence is factual, not interpretive.

---

### Debt

**Definition**  
*Debt* is an **explicitly accepted deviation** from desired quality or completeness,
approved by a human and recorded for traceability.

Debt:

- is intentional
- is owned
- is never implicit

---

### Determinism

**Definition**  
*Determinism* means that given the same inputs,
the system produces the same outputs without hidden variability.

---

### Traceability

**Definition**  
*Traceability* is the ability to follow any output back to:

- inputs
- decisions
- rules
- evidence

Traceability is mandatory, not optional.

---

## 4. Terminology Rules

- Terms defined here **must be used consistently**.
- Forbidden interpretations **must not** appear in documentation, artifacts, or code.
- New terms **must be added here before use**.

---

## 5. Change Policy

This document is versioned.

Changes:

- must be explicit
- must not silently redefine existing terms
- may require updates to plans, tests, or reviews
