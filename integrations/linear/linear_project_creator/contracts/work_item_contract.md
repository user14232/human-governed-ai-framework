# WORK ITEM CONTRACT

## Purpose

This document defines the **content quality requirements** for work items created using the Linear template.

The template enforces **structural validity**.
This contract enforces **semantic quality and agent usability**.

All agents generating or modifying work items must follow this contract.

If any rule in this contract conflicts with free-form interpretation, **the contract takes precedence**.

---

# Core Principle

Work items must describe:

**Intent, scope, and constraints — not implementation details.**

Work items must enable the DevOS workflow pipeline:

```
Story
 → PLANNING
 → ARCH_CHECK
 → TEST_DESIGN
 → IMPLEMENTATION
```

Stories provide the input for planning.
They must not prescribe the implementation strategy unless explicitly restricted.

---

# Work Item Hierarchy

```
Project
  → Epic
      → Story
          → Task
```

Each level has a specific responsibility.

---

# Epic Contract

## Purpose

An Epic represents a **coherent capability, workstream, or architectural milestone**.

It groups stories that contribute to a shared outcome.

## Requirements

An Epic must:

• Describe a clear problem domain or capability
• Define the expected system outcome
• Contain multiple stories (minimum: 2)
• Avoid implementation details

## Epic Description

The Epic description must explain:

• the capability being introduced or improved
• why the change is necessary
• the expected system-level impact

## Epic Acceptance Criteria

Epic acceptance criteria must describe:

• observable system outcomes
• integration expectations
• completion conditions for the Epic

---

# Story Contract

## Purpose

A Story represents a **single deliverable capability or behaviour change**.

Stories are the **primary input for the DevOS planning pipeline**.

Stories must contain sufficient context to enable automated planning and architecture validation.

---

# Story Required Fields

Each Story must define the following fields.

---

## Problem Statement

The problem statement explains **why the story exists**.

It must describe the deficiency, limitation, or missing capability in the current system.

A valid problem statement:

• identifies the issue clearly
• describes the impact
• avoids proposing a solution

Example:

Bad:

```
Add a workflow parser class.
```

Good:

```
Workflow definitions currently exist as YAML files but cannot be
interpreted by the runtime engine.
The runtime therefore cannot execute workflow transitions.
```

---

## Scope

Scope defines **what the story includes**.

It establishes the boundary for the implementation plan.

A good scope:

• describes the capability being implemented
• defines the functional boundary
• avoids implementation decisions

Example:

```
Implement runtime parsing of workflow definition YAML files
into typed workflow structures used by the runtime engine.
```

---

## Constraints

Constraints define **technical or architectural limitations** that must be respected.

These constraints are validated during the **ARCH_CHECK stage**.

Constraints may include:

• architecture rules
• performance limitations
• compatibility requirements
• dependency restrictions

Example:

```
The implementation must not introduce dependencies from runtime/types
into runtime/engine modules.

The parsing logic must operate during run initialization only.
```

---

## Architecture Context

Architecture context identifies the **system components affected by the story**.

This information is used by the architecture validator.

It should describe:

• modules affected
• architectural layers involved
• relevant system contracts

Example:

```
Affected modules:
runtime/framework/workflow_loader

Used by:
runtime/engine/workflow_engine
```

Architecture context helps prevent **layer violations and architectural drift**.

---

## Non-Goals

Non-goals explicitly define **what the story will not address**.

This prevents scope creep during planning.

Examples:

```
This story does not introduce workflow validation.

This story does not change the runtime event model.
```

Non-goals must be clear and explicit.

---

## Design Freedom

Design freedom indicates how much architectural freedom the implementation agent has.

Allowed values:

```
high
restricted
```

### high

The implementation agent may design the solution architecture.

Used for:

• new capabilities
• exploratory features
• flexible implementation problems

### restricted

The solution approach is already constrained.

Used for:

• architecture-sensitive areas
• domain model definitions
• compliance-critical components

Example:

```
Design freedom: restricted
```

---

# Story Acceptance Criteria

Story acceptance criteria must describe **observable outcomes**.

They must:

• be verifiable
• describe behaviour rather than implementation
• define completion conditions

Example:

```
- Workflow YAML files are successfully parsed.
- WorkflowDefinition structures are produced.
- Runtime engine can access parsed workflow transitions.
```

---

# Task Contract

## Purpose

Tasks represent **implementation steps required to complete a Story**.

Tasks are execution-level units.

---

## Task Requirements

A Task must:

• represent a concrete development action
• be executable without further decomposition
• affect a limited set of files or components

Examples of valid tasks:

```
Implement WorkflowDefinition structure
Implement YAML workflow parser
Add unit tests for workflow parsing
```

---

## Task Definition of Done

Every Task must define a `done_criteria` field.

`done_criteria` describes the **verifiable outcome** that proves the task is complete.

It must reference one of:

• a concrete output artifact (file, module, test file) that was produced
• a passing test result or test suite
• an observable system state (e.g. "all existing tests pass without modification")

Example:

```
done_criteria: |
  runtime/types.py exposes RunId, WorkflowState, ArtifactRecord, EventEnvelope,
  DecisionEntry, and GateResult as frozen dataclasses.
  All existing unit tests continue to pass.
```

`done_criteria` enables deterministic task handoff and supports agentive execution
without ambiguity about what "done" means.

---

# Epic Dependency Modeling

Epics may declare explicit sequencing dependencies using the `blocks` field.

`blocks` is a list of **epic names** that cannot begin until this epic is complete.

Example:

```yaml
- name: "Implement Runtime Core Modules"
  blocks:
    - "Implement Workflow Gates and Events"
```

This means "Runtime Core Modules" must be fully done before "Workflow Gates and Events"
can start.

## Rules

• `blocks` references must name epics defined in the same YAML project file (validated
  by `EPIC_BLOCKS_VALID`).
• Multi-epic projects without any `blocks` declaration trigger `PROJECT_NO_EPIC_DEPS`.
• Circular dependencies are not detected at parse time; avoid them by design.
• Declare only genuine hard dependencies; soft preferences are not modeled here.

`blocks` declarations are resolved to Linear `blocks` issue relations after all
issues are created.

---

# Story Dependency Modeling

Stories may declare explicit dependencies using the `blocks` field.

`blocks` is a list of **story names** that cannot begin until this story is complete.

Example:

```yaml
- name: "Implement shared types and framework loaders"
  blocks:
    - "Implement run engine lifecycle"
    - "Implement store and artifact system behavior"
```

This means "shared types" must be done before the dependent stories can start.

## Rules

• `blocks` references must name stories defined in the same YAML project file (validated
  by `STORY_BLOCKS_VALID`).
• Unresolvable names are logged as warnings at build time; they do not fail the build.
• Circular dependencies are not detected at parse time; avoid them by design.

`blocks` declarations are resolved to Linear `blocks` issue relations after all
issues are created. This makes dependency order visible in Linear's issue graph.

---

# Granularity Rules

The following granularity rules should be respected.

Epic:

2–10 stories

Story:

2–7 tasks

Task:

single implementation step

---

# Test Task Obligation

Every Story that changes runtime behavior must contain at least one task with a
test-oriented name. Accepted keywords: `test`, `verify`, `validate`, `spec`, `check`.

This is enforced by `STORY_MISSING_TEST_TASK`.

Rationale: bundling "implement X" and "tests pass" into one task produces ambiguous
done states and makes test outcomes non-attributable. Verification must be a separate,
independently completable unit of work.

Example:

```yaml
tasks:
  - name: "Implement workflow transition logic"
    done_criteria: "workflow_engine advances one transition per call."
  - name: "Write unit tests for workflow transitions"
    done_criteria: "All transition paths covered. Test suite passes with no failures."
```

---

# Anti-Patterns

The following patterns must be avoided.

## Epic Anti-Patterns

• Epic containing only one story
• Epic describing a single implementation task
• Multi-epic project with no `blocks` declarations (implicit ordering is invisible)

---

## Story Anti-Patterns

• Story describing only implementation mechanics
• Story containing multiple unrelated capabilities — "AND" stories
• Story with no test task (verification evidence missing)
• Symmetric decomposition: forcing every epic to have exactly N stories signals
  template-following, not genuine problem decomposition. Story count must reflect
  the actual problem scope. Two stories and seven stories are equally valid if
  each story represents a coherent deliverable.

Bad example:

```
Refactor parser and implement new workflow engine logic.
```

---

## Task Anti-Patterns

• Task describing multiple unrelated actions

Bad example:

```
Implement parser, add tests, and refactor event system.
```

---

# Label Usage

The following labels are expected:

```
epic
story
task
bug
```

Work items must use appropriate labels for classification.

---

# Effort and Complexity

Stories must define:

```
effort
complexity
```

The estimate is calculated automatically:

```
estimate = effort + complexity
```

Effort describes **implementation size**.

Complexity describes **uncertainty or architectural difficulty**.

---

# Final Rule

If a work item violates this contract, it must be **revised before entering the DevOS planning pipeline**.
