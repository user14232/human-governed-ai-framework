# WORK ITEM LINTER RULES

These rules define automated validation for generated work items.

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

• `EPIC_BLOCKS_VALID` — Every name in `epic.blocks` must reference a known epic in
  this project. Self-references are also rejected.

## Story Rules

• `STORY_REQUIRED_FIELD` — Story must include all five required DevOS planning fields:

  * problem_statement
  * scope
  * constraints
  * architecture_context
  * non_goals

• `STORY_AC_REQUIRED` — Story must contain `acceptance_criteria`.

• `STORY_AC_CHECKBOX_FORMAT` — `acceptance_criteria` must contain at least one
  `- [ ]` checkbox item. Acceptance criteria that cannot be individually checked
  off are not verifiable outcomes.

• `STORY_MISSING_TEST_TASK` — At least one task in the story must have a name
  containing a test-oriented keyword: `test`, `verify`, `validate`, `spec`, `check`.
  Implementation and verification must be represented by separate tasks.

• `STORY_BLOCKS_VALID` — Every name in `story.blocks` must reference a known story
  in this project. Self-references are also rejected.

## Task Rules

• `TASK_MULTI_ACTION` — Task name must not contain multi-action separators
  (comma or " and "). Each Task must describe a single development action.

• `TASK_MISSING_DOD` — Task must include a non-empty `done_criteria` field.
  `done_criteria` must describe the verifiable outcome that proves task completion:
  an output artifact, a passing test result, or an observable system state.

## Granularity Rules

Epic:
2–10 stories

Story:
2–7 tasks

Task:
single step
