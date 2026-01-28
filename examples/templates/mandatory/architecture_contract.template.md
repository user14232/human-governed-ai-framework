# architecture_contract.md

**Status:** REQUIRED PROJECT INPUT (mandatory)  
**Scope:** Project-provided, framework-governed input  
**Audience:** Humans, `agent_architecture_guardian`, `agent_planner`, `agent_reviewer`

---

## 1. Purpose

This document defines the **non-negotiable architecture contract** of the system.

It governs:

- system boundaries
- layering and dependency direction
- allowed and forbidden patterns
- stability guarantees

---

## 2. System Boundaries

### In Scope

- …

### Out of Scope

- …

External systems must be treated as dependencies.

---

## 3. Layers and Dependency Rules

Define conceptual layers and **allowed dependency directions**.

- Layer A may depend on Layer B
- Layer B must not depend on Layer C

No cyclic dependencies are allowed.

---

## 4. Allowed Patterns

Explicitly permitted architectural patterns.

- …
- …

---

## 5. Forbidden Patterns

Explicitly forbidden patterns.

- …
- …

If a pattern is forbidden here, it **must not** be used even if convenient.

---

## 6. Stability Guarantees

List elements that are:

- guaranteed stable
- expected to evolve only via governed change

---

## 7. Change Policy

Architecture changes:

- are not errors
- must be explicit
- require a versioned proposal and human approval
