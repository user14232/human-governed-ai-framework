# source_policy.md

**Status:** REQUIRED PROJECT INPUT (mandatory)  
**Scope:** Project-provided, framework-governed input  
**Audience:** Humans, `agent_planner`, `agent_test_designer`, `agent_reviewer`

---

## 1. Purpose

This document defines **which sources are considered valid**,  
**how conflicts are resolved**, and **which sources are forbidden**.

It establishes a **hierarchy of truth** for the project.

---

## 2. Sources of Truth (Allowed)

Each source must be explicitly listed.

- SRC-001: [Source name or system]
- SRC-002: [Source name or system]

Each source should include:

- ownership (internal / external)
- stability expectation (stable / volatile)

---

## 3. Priority Order

When multiple sources conflict, **this order applies**:

1. SRC-001
2. SRC-002
3. …

No implicit prioritization is allowed.

---

## 4. Conflict Resolution Rules

Define what happens if:

- sources disagree
- data is incomplete
- data is outdated

Rules must be explicit and deterministic.

---

## 5. Allowed Evidence Types

Examples:

- peer-reviewed studies
- official statistics
- contractual documents
- logged system outputs

---

## 6. Forbidden Sources

List sources that must **never** be used.

Examples:

- social media
- undocumented assumptions
- marketing material
- unverifiable personal opinions

---

## 7. Change Policy

Changes to this document:

- must be explicit
- must be versioned
- may require downstream updates
