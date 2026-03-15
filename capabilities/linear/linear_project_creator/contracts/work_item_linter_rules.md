# WORK ITEM LINTER RULES

These rules define automated validation for generated work items.

All rules are enforced deterministically. No heuristics. No LLM reasoning.

## Project-Level Rules

• `PROJECT_NO_EPIC_DEPS` — A project with more than one epic must declare at least
  one epic-level `blocks` dependency. Implicit execution order is not visible to
  the team or to automated tooling.

## Epic Rules

• `EPIC_MIN_STORIES` — Epic must contain at least 2 stories.

• `EPIC_MAX_STORIES` — Epic must contain no more than 10 stories.

• `EPIC_DESC_MIN_WORDS` — Epic description must contain at least 20 words.
  An Epic description must explain: (1) the capability being introduced or improved,
  (2) why the change is necessary, and (3) the expected system-level impact.

• `EPIC_MISSING_MILESTONE` — Epic must be assigned to a milestone when the project
  defines milestones. Each epic must be anchored to a delivery milestone to make
  its timeline explicit.

• `EPIC_AC_CHECKBOX_FORMAT` — Epic `acceptance_criteria` must contain at least one
  `- [ ]` checkbox item. Criteria that cannot be individually checked off are not
  verifiable outcomes. Mirrors the `STORY_AC_CHECKBOX_FORMAT` requirement at the
  Epic level.

  Example:
  ```
  - [ ] Gate evaluator enforces all four check types in fixed order.
  - [ ] Workflow state advances by exactly one transition per call.
  ```

• `EPIC_BLOCKS_VALID` — Every name in `epic.blocks` must reference a known epic in
  this project. Self-references are also rejected.

• `EPIC_BLOCKS_CYCLE` — `epic.blocks` declarations must not form a directed cycle.
  Circular epic dependencies make the execution order undefined and prevent automated
  planning. The linter reports the detected cycle path when this rule fires.

## Story Rules

• `STORY_REQUIRED_FIELD` — Story must include all five required DevOS planning fields:

  * problem_statement
  * scope
  * constraints
  * architecture_context
  * non_goals

• `STORY_DESIGN_FREEDOM_REQUIRED` — Story must define `design_freedom` with a value
  of `high` or `restricted`. This field is required (not optional) for DevOS pipeline
  input. It declares whether the implementation agent may design the solution approach
  (`high`) or must follow the prescribed architecture (`restricted`). Absent or empty
  values trigger this rule.

• `STORY_DESIGN_FREEDOM` — When `design_freedom` is present, its value must be exactly
  `high` or `restricted` (case-insensitive). Other values are rejected.

• `STORY_AC_REQUIRED` — Story must contain `acceptance_criteria`.

• `STORY_AC_CHECKBOX_FORMAT` — `acceptance_criteria` must contain at least one
  `- [ ]` checkbox item. Acceptance criteria that cannot be individually checked
  off are not verifiable outcomes.

• `STORY_TASK_MIN` — Story must contain at least 2 tasks.

• `STORY_TASK_MAX` — Story must contain no more than 7 tasks.

• `STORY_MISSING_TEST_TASK` — At least one task in the story must satisfy the
  verification requirement using one of two mechanisms:

  1. **Explicit**: set `task_type: verification` on the task (preferred).
  2. **Keyword**: task name contains a keyword from: `test`, `verify`, `validate`,
     `spec`, `check`.

  Implementation and verification must be represented by separate tasks to produce
  explicit, attributable evidence. Bundling implementation and test evidence into
  one task produces ambiguous done states.

• `STORY_BLOCKS_VALID` — Every name in `story.blocks` must reference a known story
  in this project. Self-references are also rejected.

• `STORY_BLOCKS_CYCLE` — `story.blocks` declarations must not form a directed cycle.
  Circular story dependencies make the execution order undefined and prevent automated
  planning. The linter reports the detected cycle path when this rule fires.

## Task Rules

• `TASK_MULTI_ACTION` — Task name must not contain multi-action separators
  (comma or " and "). Each Task must describe a single development action.

• `TASK_MISSING_DOD` — Task must include a non-empty `done_criteria` field.
  `done_criteria` must describe the verifiable outcome that proves task completion:
  an output artifact, a passing test result, or an observable system state.

• `TASK_TYPE_VALID` — When `task_type` is present, its value must be exactly
  `implementation` or `verification` (case-insensitive). Other values are rejected.

  Semantics:
  - `implementation` — task produces a code artifact or system change.
  - `verification`   — task produces test evidence; automatically satisfies the
                       `STORY_MISSING_TEST_TASK` requirement without keyword matching
                       in the task name.

## Granularity Rules

Epic:
2–10 stories

Story:
2–7 tasks

Task:
single step
