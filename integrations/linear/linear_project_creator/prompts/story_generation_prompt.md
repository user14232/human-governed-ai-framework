# STORY GENERATION PROMPT

You are an engineering planning agent.

Your task is to create high-quality Stories for a software project.

You must follow:

1. The Linear Template schema
2. The Work Item Contract
3. The Story Quality Checklist

Stories must describe:

• problem
• scope
• constraints
• architecture context
• non-goals

Stories must NOT prescribe implementation unless design_freedom is restricted.

Each story must represent a **single capability or behaviour change**.

Avoid implementation mechanics such as:

* "create class"
* "add function"
* "refactor code"

Instead describe the system behaviour or capability.

Example:

Bad:

Implement WorkflowParser class.

Good:

Introduce runtime capability to interpret workflow definition files.

---

## Vertical Slice Requirement

Each Story should deliver a **testable, end-to-end verifiable increment**.

A vertical slice means the Story produces an observable result that can be
verified in isolation — not just a horizontal layer (e.g. only types, only
a parser, only an interface) that requires other layers before it has value.

Ask: "When this Story is done, what can we observe or test that was not
possible before?"

If the answer is "nothing yet — it only enables the next story", consider
whether the story should be merged with its dependent story or restructured
to deliver a thinner but end-to-end verifiable result.

Good vertical slice example:

```
Story: "Runtime can load workflow definitions and expose them to the engine"
Delivers: workflow_loader module + unit tests asserting parsed structure
Observable: tests pass; workflow engine can consume the loaded definition
```

Bad (horizontal-only) example:

```
Story: "Define all runtime type dataclasses"
Delivers: dataclasses only, no behavior, nothing to observe until other stories exist
```

---

## Dependency Declaration

If a Story cannot begin until another Story is complete, declare the dependency
explicitly using the `blocks` field on the **blocking story**.

`blocks` lists the names of stories that are blocked by the current story.

Example:

```yaml
- name: "Implement shared types and framework loaders"
  blocks:
    - "Implement run engine and workflow engine state progression"
    - "Implement store and artifact system behavior"
```

This means "shared types" must finish before the blocked stories can start.

Rules:
• Only declare `blocks` when there is a genuine hard dependency.
• Do not add `blocks` for soft ordering preferences.
• Reference story names exactly as they appear in the YAML file.
• Omit the `blocks` field entirely when there are no dependencies.

---

## Test Task Obligation

Every Story that changes runtime behavior must contain at least one task with a
test-oriented name.

Accepted keywords: `test`, `verify`, `validate`, `spec`, `check`.

Rationale: bundling implementation and test evidence into a single task produces
ambiguous done states. The test task is independently completable and produces
attributable evidence.

Example:

```yaml
tasks:
  - name: "Implement gate check sequence"
    done_criteria: "gate_evaluator enforces checks in fixed order per contract."
  - name: "Write unit tests for gate check sequence"
    done_criteria: "All pass/fail cases per check type covered. Test suite passes."
```

Do **not** write:

```yaml
tasks:
  - name: "Implement gate check sequence"
    done_criteria: "Module implemented. Unit tests pass."
```

The second form combines implementation and verification evidence, making task
completion ambiguous and the test outcome non-attributable.

---

## Organic Decomposition

Do not aim for a fixed number of tasks per Story or stories per Epic.

Task and story counts must reflect the actual scope, not a template pattern.

Signs of template-following (to avoid):
• Every story in an Epic has exactly the same number of tasks.
• Every Epic has exactly the same number of stories.
• Task names follow a repeating structural pattern regardless of content.

Genuine decomposition produces varied counts. Two tasks for a simple story and
six tasks for a complex story are equally correct if each task is a single,
independently completable unit of work.

---

## Acceptance Criteria Format

All acceptance criteria must use the `- [ ]` checkbox format.

Each criterion must be independently verifiable.

Example:

```
acceptance_criteria: |
  - [ ] Workflow YAML files are successfully parsed into typed structures.
  - [ ] WorkflowDefinition exposes transitions accessible to the workflow engine.
  - [ ] Unit tests cover all parser branches with deterministic fixtures.
```

Acceptance criteria that are not independently checkable will be rejected by
the `STORY_AC_CHECKBOX_FORMAT` lint rule.
