# EPIC GENERATION PROMPT

You are responsible for creating Epics for a software system.

Epics must represent:

• capabilities
• architectural milestones
• coherent workstreams

An Epic must not represent:

• a single task
• a technical refactor without system impact
• an implementation detail

Each Epic must contain multiple Stories.

---

## Epic Description Requirements

Epic descriptions must be substantive. A description of fewer than 20 words is rejected
by the linter (`EPIC_DESC_MIN_WORDS`).

An Epic description must explicitly cover all three of the following:

### 1. Capability introduced or improved

State what the system gains or what deficiency is resolved.

Example:

```
The runtime currently cannot evaluate gate conditions or track workflow progression.
This Epic introduces the gate evaluator and workflow engine modules that enable
deterministic, contract-compliant workflow execution.
```

### 2. Why the change is necessary

State the problem or gap that makes this Epic necessary. Reference the architecture
or contracts that require it.

Example:

```
Without gate enforcement, agents can proceed to subsequent workflow states without
satisfying preconditions, violating the framework compliance contract.
```

### 3. Expected system-level impact

State the observable, system-level outcome once the Epic is complete.

Example:

```
After this Epic, the runtime enforces all four gate check types in fixed order and
advances workflow state deterministically with one transition per advance call.
```

---

## Epic Acceptance Criteria

Epic acceptance criteria must describe:

• observable system outcomes
• integration expectations
• completion conditions for the Epic

Each criterion **must** use the `- [ ]` checkbox format so it is independently
verifiable. Enforced by `EPIC_AC_CHECKBOX_FORMAT`.

Example:

```
acceptance_criteria: |
  - [ ] Gate evaluator enforces all four check types in fixed order.
  - [ ] Workflow state advances by exactly one transition per advance call.
  - [ ] All compliance checks pass with deterministic test fixtures.
```

---

---

## Epic Dependency Declaration

If this Epic cannot begin until another Epic is complete, declare the dependency
explicitly using the `blocks` field on the **blocking Epic**.

`blocks` lists the names of Epics that are blocked by the current Epic.

Example:

```yaml
- name: "Implement Runtime Core Modules"
  blocks:
    - "Implement Workflow Gates and Events"
```

Rules:
• Only declare `blocks` when there is a genuine hard dependency.
• Do not add `blocks` for soft ordering preferences.
• Reference Epic names exactly as they appear in the YAML file.
• Omit the `blocks` field entirely when there are no dependencies.

Multi-epic projects without any `blocks` declarations trigger `PROJECT_NO_EPIC_DEPS`.

---

## Epic Milestone Assignment

Every Epic must be assigned to a milestone when the project defines milestones.
The milestone anchors the Epic's delivery expectation in the project timeline.

```yaml
milestone: "Phase 1 Core Complete"
```

Epics without milestone assignment trigger `EPIC_MISSING_MILESTONE`.

---

## Anti-Patterns

Avoid these patterns in Epic descriptions:

• A single sentence restating the Epic title
• A description that only lists stories or tasks
• Vague outcomes ("improves the system", "adds functionality")
• Implementation mechanics ("create a class", "add a method")
• Symmetric story counts: do not aim for a specific number of stories per Epic.
  Story count must reflect the actual problem scope, not a template pattern.
