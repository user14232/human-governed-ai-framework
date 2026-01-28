# domain_rules.md  

**Status:** REQUIRED PROJECT INPUT (mandatory)  
**Scope:** Project-provided, framework-governed input  
**Audience:** Humans, `agent_planner`, `agent_test_designer`, `agent_reviewer`, `agent_architecture_guardian`

---

## 1. Purpose

This document defines **hard, non-negotiable domain invariants** that must **never be violated** by
planning, implementation, testing, or architecture decisions.

These rules are treated as **absolute constraints**, not preferences or guidelines.

The framework:

- requires this document to exist
- requires the rules to be explicit and referenceable
- does **not** interpret or validate domain semantics

---

## 2. Normative Requirements (Non-Negotiable)

All domain rules **MUST** comply with the following requirements.

### 2.1 Rule identity

- Every rule **MUST** have a **stable, unique identifier**
- Rule IDs **MUST NOT** change once referenced
- Rule IDs **MUST** be used when:
  - designing tests
  - reviewing implementations
  - recording violations or accepted debt

**Format (recommended, not enforced):**
DR-001, DR-002, …

Example:

```text
DR-001
DR-002
...
```

---

### 2.2 Atomicity

- Each rule **MUST** express **exactly one invariant**
- Compound rules (multiple conditions, multiple outcomes) are **forbidden**
- If multiple constraints exist, they **MUST** be split into multiple rules

---

### 2.3 Normative language

- Rules **MUST** be written using **normative language**
- Allowed forms:
  - `MUST`
  - `MUST NOT`
- Disallowed forms:
  - `SHOULD`
  - `MAY`
  - `GENERALLY`
  - vague qualifiers (“usually”, “ideally”, “as much as possible”)

---

### 2.4 Negative formulation (testability)

- Each rule **MUST** be formulatable as a **violation**
- A reader **MUST** be able to answer:
  > “How do we know this rule has been broken?”

Rules that cannot be violated in a detectable way are invalid.

---

### 2.5 Determinism and clarity

- Rules **MUST** be:
  - explicit
  - unambiguous
  - context-independent
- Rules **MUST NOT** rely on:
  - implicit domain knowledge
  - unstated assumptions
  - external interpretation not referenced explicitly

---

### 2.6 Stability guarantee

- Domain rules are assumed to be **stable**
- Changes to existing rules:
  - **MUST** be explicit
  - **MUST** be versioned
  - **MUST** be reflected in downstream artifacts (plans, tests, reviews)

Silent modification or reinterpretation of rules is forbidden.

---

## 3. Rule Set

All rules **MUST** be listed in this section.

### Rule format (mandatory)

Each rule **MUST** follow this structure:

```text
<RULE_ID>: <Short descriptive title>

Statement
A single, explicit, normative sentence describing the invariant.

Violation condition
A clear description of what constitutes a violation of this rule.
```

---

### Example (illustrative only, non-normative)

DR-001: No silent data loss
Statement
The system MUST NOT discard input data without explicit error reporting.

Violation condition
Any execution path where input data is ignored, dropped, or overwritten
without a recorded error or rejection.

---

## 4. Explicit Non-Rules

This document **MUST NOT** contain:

- implementation details
- architectural preferences (unless they are absolute invariants)
- workflow descriptions
- quality goals or heuristics
- performance targets (unless violation is explicit and testable)

If something is negotiable, contextual, or subject to trade-offs,
it **does not belong here**.

---

## 5. Cross-References (Required)

Each rule **SHOULD** be referenced by:

- test cases (`test_design.yaml`)
- review findings (`review_result.md`)
- architecture checks (if applicable)

References must use the **rule ID**, not free text.

---

## 6. Change Policy

- This document is a **mandatory project input**
- Any change:
  - creates a new version of this document
  - may require plan, test, or architecture updates
- Changes **MUST NOT** be applied implicitly or retroactively

---

## 7. Failure Modes (Guidance)

Common invalid patterns:

- rules without IDs
- multiple constraints in one rule
- descriptive text without normative force
- rules that cannot be violated or tested
- hidden assumptions disguised as “obvious”

Presence of such patterns indicates **invalid input quality**.

---

## 8. Framework Alignment Statement

This document is designed to ensure that:

- planners do not infer missing constraints
- test designers can map rules deterministically
- reviewers evaluate compliance, not intent
- architecture governance remains explicit

If a rule cannot be enforced, reviewed, or tested,
it **does not qualify as a domain rule** in this framework.
