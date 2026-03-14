"""
Semantic quality linter for parsed work items.

Responsibilities:
  - Apply rules from contracts/work_item_linter_rules.md to a parsed ProjectModel.
  - Return a complete list of LintViolation objects for all detected violations.
  - Never modify the input model.
  - All checks are deterministic: no heuristics, no LLM calls.

Rules enforced (rule_id → source section):

  Project-level:
  PROJECT_NO_EPIC_DEPS    Multi-epic project must declare at least one epic-level
                          'blocks' dependency. Implicit sequencing is invisible to
                          the team and to automated tooling.

  Epic-level:
  EPIC_MIN_STORIES        Epic must contain at least 2 stories.
  EPIC_MAX_STORIES        Epic must contain no more than 10 stories.
  EPIC_DESC_MIN_WORDS     Epic description must contain at least 20 words.
  EPIC_MISSING_MILESTONE  Epic must be assigned to a milestone when the project
                          defines milestones.
  EPIC_AC_CHECKBOX_FORMAT acceptance_criteria must contain at least one "- [ ]"
                          checkbox item to ensure verifiable, independently
                          checkable outcomes.
  EPIC_BLOCKS_VALID       Every name in epic.blocks must reference a known epic
                          in this project.
  EPIC_BLOCKS_CYCLE       epic.blocks declarations must not form a directed cycle.

  Story-level:
  STORY_REQUIRED_FIELD    Story must include all DevOS planning fields:
                          problem_statement, scope, constraints,
                          architecture_context, non_goals.
  STORY_DESIGN_FREEDOM_REQUIRED
                          Story must define 'design_freedom' ("high" or "restricted").
                          This field declares the implementation agent's design
                          latitude and is required for DevOS pipeline input.
  STORY_DESIGN_FREEDOM    design_freedom, when present, must be "high" or "restricted".
  STORY_AC_REQUIRED       Story must include acceptance_criteria.
  STORY_AC_CHECKBOX_FORMAT acceptance_criteria must contain at least one "- [ ]"
                          checkbox item to ensure verifiable outcomes.
  STORY_TASK_MIN          Story must contain at least 2 tasks.
  STORY_TASK_MAX          Story must contain no more than 7 tasks.
  STORY_MISSING_TEST_TASK At least one task in the story must have a name containing
                          a test-oriented keyword (test, verify, validate, spec, check)
                          OR declare task_type="verification". Implementation and
                          verification must be represented by separate tasks to produce
                          explicit, attributable evidence.
  STORY_BLOCKS_VALID      Every name in story.blocks must reference a known story
                          in this project.
  STORY_BLOCKS_CYCLE      story.blocks declarations must not form a directed cycle.

  Task-level:
  TASK_MULTI_ACTION       Task name must not contain multi-action separators
                          (comma or " and "), to keep one action per task.
  TASK_MISSING_DOD        Task must include a non-empty done_criteria field describing
                          the verifiable outcome that defines task completion.
  TASK_TYPE_VALID         task_type, when present, must be "implementation" or
                          "verification". Invalid values are rejected.

Contract reference: contracts/work_item_contract.md
Linter rules reference: contracts/work_item_linter_rules.md
"""

from __future__ import annotations

from dataclasses import dataclass

from models import EpicModel, ProjectModel, StoryModel, TaskModel


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LintViolation:
    """A single rule violation detected in a work item."""
    context: str   # e.g. "epics[0] ('My Epic')", "epics[0].stories[1] ('My Story')"
    rule_id: str   # machine-readable rule identifier, e.g. "EPIC_MIN_STORIES"
    message: str   # human-readable description of the violation


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_project(project: ProjectModel) -> list[LintViolation]:
    """
    Run all work item linter rules against *project*.

    Builds cross-reference lookup sets once, then passes them into per-level
    lint functions to enable reference validation without repeated traversal.

    Returns a list of LintViolation objects.
    An empty list means the project passes all quality checks.
    """
    violations: list[LintViolation] = []

    # Build lookup sets used for cross-reference validation.
    all_epic_names: frozenset[str] = frozenset(epic.name for epic in project.epics)
    all_story_names: frozenset[str] = frozenset(
        story.name
        for epic in project.epics
        for story in epic.stories
    )
    project_defines_milestones = len(project.milestones) > 0

    # Build blocks graphs for cycle detection (name → names-it-blocks).
    epic_blocks_graph: dict[str, tuple[str, ...]] = {
        epic.name: epic.blocks
        for epic in project.epics
        if epic.blocks
    }
    story_blocks_graph: dict[str, tuple[str, ...]] = {
        story.name: story.blocks
        for epic in project.epics
        for story in epic.stories
        if story.blocks
    }

    _lint_project_level(project, all_epic_names, violations)
    _lint_epic_blocks_cycle(epic_blocks_graph, all_epic_names, violations)
    _lint_story_blocks_cycle(story_blocks_graph, all_story_names, violations)

    for epic_idx, epic in enumerate(project.epics):
        _lint_epic(
            epic, epic_idx,
            all_epic_names=all_epic_names,
            all_story_names=all_story_names,
            project_defines_milestones=project_defines_milestones,
            violations=violations,
        )

    return violations


# ---------------------------------------------------------------------------
# Project-level rules
# ---------------------------------------------------------------------------


def _lint_project_level(
    project: ProjectModel,
    all_epic_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    context = f"project ({project.name!r})"

    if len(project.epics) > 1:
        any_epic_has_blocks = any(epic.blocks for epic in project.epics)
        if not any_epic_has_blocks:
            violations.append(LintViolation(
                context=context,
                rule_id="PROJECT_NO_EPIC_DEPS",
                message=(
                    f"Project has {len(project.epics)} epics but no epic declares a "
                    "'blocks' dependency. Multi-epic projects must express sequencing "
                    "constraints explicitly using 'blocks' on the blocking epic. "
                    "Implicit execution order is invisible to the team and to automated "
                    "tooling, making parallel-start mistakes undetectable."
                ),
            ))


# ---------------------------------------------------------------------------
# Cycle detection helpers
# ---------------------------------------------------------------------------


def _find_cycle_in_blocks_graph(
    name_to_blocks: dict[str, tuple[str, ...]],
    all_known_names: frozenset[str],
) -> list[str] | None:
    """
    Detect a cycle in a directed dependency graph using DFS.

    name_to_blocks maps each item name to the names it blocks (outgoing edges).
    Only names present in all_known_names are traversed; unknown references that
    would already be caught by BLOCKS_VALID are silently skipped.

    Returns the cycle as a list of names [A, B, ..., A] where the last element
    equals the first (the repeated entry point), or None if the graph is acyclic.
    """
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def _dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in name_to_blocks.get(node, ()):
            if neighbor not in all_known_names:
                continue  # unknown ref — already reported by BLOCKS_VALID
            if neighbor not in visited:
                if _dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                path.append(neighbor)  # close the cycle
                return True
        path.pop()
        rec_stack.discard(node)
        return False

    for node in sorted(all_known_names):  # sorted for deterministic output
        if node not in visited:
            if _dfs(node):
                return path  # contains the cycle path
    return None


def _lint_epic_blocks_cycle(
    epic_blocks_graph: dict[str, tuple[str, ...]],
    all_epic_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    if not epic_blocks_graph:
        return
    cycle = _find_cycle_in_blocks_graph(epic_blocks_graph, all_epic_names)
    if cycle is not None:
        cycle_str = " → ".join(repr(n) for n in cycle)
        violations.append(LintViolation(
            context="project (epic blocks graph)",
            rule_id="EPIC_BLOCKS_CYCLE",
            message=(
                f"Circular dependency detected in epic 'blocks' declarations: {cycle_str}. "
                "Cyclic dependencies make the execution order undefined and prevent "
                "automated planning. Remove the cycle by revising the 'blocks' fields."
            ),
        ))


def _lint_story_blocks_cycle(
    story_blocks_graph: dict[str, tuple[str, ...]],
    all_story_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    if not story_blocks_graph:
        return
    cycle = _find_cycle_in_blocks_graph(story_blocks_graph, all_story_names)
    if cycle is not None:
        cycle_str = " → ".join(repr(n) for n in cycle)
        violations.append(LintViolation(
            context="project (story blocks graph)",
            rule_id="STORY_BLOCKS_CYCLE",
            message=(
                f"Circular dependency detected in story 'blocks' declarations: {cycle_str}. "
                "Cyclic dependencies make the execution order undefined and prevent "
                "automated planning. Remove the cycle by revising the 'blocks' fields."
            ),
        ))


# ---------------------------------------------------------------------------
# Epic rules
# ---------------------------------------------------------------------------


_EPIC_MIN_STORIES = 2
_EPIC_MAX_STORIES = 10
_EPIC_DESC_MIN_WORDS = 20


def _lint_epic(
    epic: EpicModel,
    epic_idx: int,
    *,
    all_epic_names: frozenset[str],
    all_story_names: frozenset[str],
    project_defines_milestones: bool,
    violations: list[LintViolation],
) -> None:
    context = f"epics[{epic_idx}] ({epic.name!r})"
    story_count = len(epic.stories)

    if story_count < _EPIC_MIN_STORIES:
        violations.append(LintViolation(
            context=context,
            rule_id="EPIC_MIN_STORIES",
            message=(
                f"Epic contains {story_count} story/stories; "
                f"minimum is {_EPIC_MIN_STORIES}. "
                "An Epic must group multiple stories into a coherent workstream."
            ),
        ))

    if story_count > _EPIC_MAX_STORIES:
        violations.append(LintViolation(
            context=context,
            rule_id="EPIC_MAX_STORIES",
            message=(
                f"Epic contains {story_count} stories; "
                f"maximum is {_EPIC_MAX_STORIES}. "
                "Consider splitting this Epic into smaller, more focused Epics."
            ),
        ))

    _lint_epic_description(epic, context, violations)
    _lint_epic_acceptance_criteria(epic, context, violations)
    _lint_epic_milestone(epic, context, project_defines_milestones, violations)
    _lint_epic_blocks(epic, context, all_epic_names, violations)

    for story_idx, story in enumerate(epic.stories):
        _lint_story(story, epic_idx, story_idx, all_story_names, violations)


def _lint_epic_description(
    epic: EpicModel,
    context: str,
    violations: list[LintViolation],
) -> None:
    word_count = len(epic.description.split()) if epic.description else 0
    if word_count < _EPIC_DESC_MIN_WORDS:
        violations.append(LintViolation(
            context=context,
            rule_id="EPIC_DESC_MIN_WORDS",
            message=(
                f"Epic description contains {word_count} word(s); "
                f"minimum is {_EPIC_DESC_MIN_WORDS}. "
                "An Epic description must explain the capability being introduced, "
                "why the change is necessary, and the expected system-level impact."
            ),
        ))


def _lint_epic_acceptance_criteria(
    epic: EpicModel,
    context: str,
    violations: list[LintViolation],
) -> None:
    """
    EPIC_AC_CHECKBOX_FORMAT — Epic acceptance_criteria must use "- [ ]" checkbox format.

    Epic AC is required by the parser (structural validation), so only the format
    check is needed here. Mirrors the STORY_AC_CHECKBOX_FORMAT rule.
    """
    if "- [ ]" not in epic.acceptance_criteria:
        violations.append(LintViolation(
            context=context,
            rule_id="EPIC_AC_CHECKBOX_FORMAT",
            message=(
                "Epic 'acceptance_criteria' contains no checkbox items ('- [ ]'). "
                "Each acceptance criterion must be a verifiable, independently "
                "checkable outcome formatted as a Markdown task list item. "
                "Example: '- [ ] Gate evaluator enforces all four check types.'"
            ),
        ))


def _lint_epic_milestone(
    epic: EpicModel,
    context: str,
    project_defines_milestones: bool,
    violations: list[LintViolation],
) -> None:
    if project_defines_milestones and epic.milestone is None:
        violations.append(LintViolation(
            context=context,
            rule_id="EPIC_MISSING_MILESTONE",
            message=(
                "Epic has no 'milestone' assignment but the project defines milestones. "
                "Every epic must be anchored to a milestone to make its delivery "
                "timeline explicit and trackable."
            ),
        ))


def _lint_epic_blocks(
    epic: EpicModel,
    context: str,
    all_epic_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    for blocked_name in epic.blocks:
        if blocked_name == epic.name:
            violations.append(LintViolation(
                context=context,
                rule_id="EPIC_BLOCKS_VALID",
                message=(
                    f"Epic 'blocks' references itself ('{blocked_name}'). "
                    "Self-referential dependencies are not meaningful."
                ),
            ))
        elif blocked_name not in all_epic_names:
            violations.append(LintViolation(
                context=context,
                rule_id="EPIC_BLOCKS_VALID",
                message=(
                    f"Epic 'blocks' references '{blocked_name}', which is not defined "
                    "as an epic in this project. Check for typos or stale references."
                ),
            ))


# ---------------------------------------------------------------------------
# Story rules
# ---------------------------------------------------------------------------


_STORY_REQUIRED_DEVOS_FIELDS: tuple[tuple[str, str], ...] = (
    ("problem_statement",    "Problem Statement"),
    ("scope",                "Scope"),
    ("constraints",          "Constraints"),
    ("architecture_context", "Architecture Context"),
    ("non_goals",            "Non-Goals"),
)

_STORY_MIN_TASKS = 2
_STORY_MAX_TASKS = 7

_STORY_DESIGN_FREEDOM_VALUES = frozenset({"high", "restricted"})

_TEST_TASK_KEYWORDS = frozenset({"test", "verify", "validate", "spec", "check"})


def _lint_story(
    story: StoryModel,
    epic_idx: int,
    story_idx: int,
    all_story_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    context = f"epics[{epic_idx}].stories[{story_idx}] ({story.name!r})"

    # Required DevOS planning fields
    for field_name, label in _STORY_REQUIRED_DEVOS_FIELDS:
        value = getattr(story, field_name, None)
        if not value or not str(value).strip():
            violations.append(LintViolation(
                context=context,
                rule_id="STORY_REQUIRED_FIELD",
                message=(
                    f"Story is missing required DevOS planning field '{field_name}' ({label}). "
                    "Stories entering the DevOS planning pipeline must define all "
                    "five planning context fields: problem_statement, scope, constraints, "
                    "architecture_context, non_goals."
                ),
            ))

    # design_freedom — required presence check (STORY_DESIGN_FREEDOM_REQUIRED)
    # then value check (STORY_DESIGN_FREEDOM) only if present but invalid
    if not story.design_freedom or not story.design_freedom.strip():
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_DESIGN_FREEDOM_REQUIRED",
            message=(
                "Story is missing required field 'design_freedom'. "
                "Allowed values: 'high' or 'restricted'. "
                "'high' means the implementation agent may design the solution approach. "
                "'restricted' means the approach is pre-determined and the agent must "
                "follow the architecture_context and constraints precisely. "
                "This field is required for DevOS PLANNING pipeline input."
            ),
        ))
    elif story.design_freedom.strip().lower() not in _STORY_DESIGN_FREEDOM_VALUES:
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_DESIGN_FREEDOM",
            message=(
                f"'design_freedom' value '{story.design_freedom}' is not valid. "
                f"Allowed values: {sorted(_STORY_DESIGN_FREEDOM_VALUES)}."
            ),
        ))

    # Acceptance criteria — presence
    if not story.acceptance_criteria or not story.acceptance_criteria.strip():
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_AC_REQUIRED",
            message=(
                "Story is missing 'acceptance_criteria'. "
                "Acceptance criteria must describe observable, verifiable outcomes "
                "that define when the Story is complete."
            ),
        ))
    elif "- [ ]" not in story.acceptance_criteria:
        # Acceptance criteria — format: must use checkbox items
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_AC_CHECKBOX_FORMAT",
            message=(
                "Story 'acceptance_criteria' contains no checkbox items ('- [ ]'). "
                "Each acceptance criterion must be a verifiable, independently "
                "checkable outcome formatted as a Markdown task list item."
            ),
        ))

    # Task granularity
    task_count = len(story.tasks)
    if task_count < _STORY_MIN_TASKS:
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_TASK_MIN",
            message=(
                f"Story contains {task_count} task(s); "
                f"minimum is {_STORY_MIN_TASKS}. "
                "Each Story must decompose into at least 2 concrete implementation tasks."
            ),
        ))

    if task_count > _STORY_MAX_TASKS:
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_TASK_MAX",
            message=(
                f"Story contains {task_count} tasks; "
                f"maximum is {_STORY_MAX_TASKS}. "
                "Consider splitting this Story into smaller Stories."
            ),
        ))

    # Test task requirement
    if task_count >= _STORY_MIN_TASKS and not _story_has_test_task(story):
        violations.append(LintViolation(
            context=context,
            rule_id="STORY_MISSING_TEST_TASK",
            message=(
                "Story contains no verification task. "
                "At least one task must either declare task_type='verification' or "
                f"have a name containing a keyword from: {sorted(_TEST_TASK_KEYWORDS)}. "
                "Implementation and verification must be separate tasks so that "
                "test outcomes are attributable and independently completable."
            ),
        ))

    # blocks reference validity
    for blocked_name in story.blocks:
        if blocked_name == story.name:
            violations.append(LintViolation(
                context=context,
                rule_id="STORY_BLOCKS_VALID",
                message=(
                    f"Story 'blocks' references itself ('{blocked_name}'). "
                    "Self-referential dependencies are not meaningful."
                ),
            ))
        elif blocked_name not in all_story_names:
            violations.append(LintViolation(
                context=context,
                rule_id="STORY_BLOCKS_VALID",
                message=(
                    f"Story 'blocks' references '{blocked_name}', which is not defined "
                    "as a story in this project. Check for typos or stale references."
                ),
            ))

    for task_idx, task in enumerate(story.tasks):
        _lint_task(task, epic_idx, story_idx, task_idx, violations)


def _story_has_test_task(story: StoryModel) -> bool:
    """
    Return True if at least one task in the story satisfies the verification requirement.

    A task satisfies the requirement if:
      (a) its task_type field is explicitly set to "verification" (semantic, preferred), or
      (b) its name contains a test-oriented keyword (keyword heuristic, legacy support).

    Detection (b) is case-insensitive substring matching against a fixed keyword set.
    This intentionally avoids grammar parsing and keeps behavior fully deterministic.
    """
    for task in story.tasks:
        # Prefer explicit semantic classification over keyword heuristic.
        if task.task_type is not None and task.task_type.strip().lower() == "verification":
            return True
        lower_name = task.name.lower()
        if any(kw in lower_name for kw in _TEST_TASK_KEYWORDS):
            return True
    return False


# ---------------------------------------------------------------------------
# Task rules
# ---------------------------------------------------------------------------


_TASK_TYPE_VALUES = frozenset({"implementation", "verification"})


def _lint_task(
    task: TaskModel,
    epic_idx: int,
    story_idx: int,
    task_idx: int,
    violations: list[LintViolation],
) -> None:
    context = (
        f"epics[{epic_idx}].stories[{story_idx}].tasks[{task_idx}] ({task.name!r})"
    )

    if _task_describes_multiple_actions(task.name):
        violations.append(LintViolation(
            context=context,
            rule_id="TASK_MULTI_ACTION",
            message=(
                f"Task name '{task.name}' appears to combine multiple unrelated actions "
                "(multi-action separator detected: comma or ' and '). "
                "Each Task must represent a single, concrete development action."
            ),
        ))

    if not task.done_criteria or not task.done_criteria.strip():
        violations.append(LintViolation(
            context=context,
            rule_id="TASK_MISSING_DOD",
            message=(
                "Task is missing 'done_criteria'. "
                "Every task must define a verifiable outcome that proves completion: "
                "an output artifact, a passing test result, or an observable system state. "
                "This enables deterministic task handoff and agentive execution."
            ),
        ))

    # task_type value validation — only when field is present
    if task.task_type is not None:
        normalized = task.task_type.strip().lower()
        if normalized not in _TASK_TYPE_VALUES:
            violations.append(LintViolation(
                context=context,
                rule_id="TASK_TYPE_VALID",
                message=(
                    f"'task_type' value '{task.task_type}' is not valid. "
                    f"Allowed values: {sorted(_TASK_TYPE_VALUES)}. "
                    "'implementation' marks a task that produces a code or system artifact. "
                    "'verification' marks a task that produces test evidence and satisfies "
                    "the STORY_MISSING_TEST_TASK requirement without keyword matching."
                ),
            ))


# ---------------------------------------------------------------------------
# Pattern detection helpers
# ---------------------------------------------------------------------------


def _task_describes_multiple_actions(name: str) -> bool:
    """
    Return True if the task name contains explicit multi-action separators.

    Detection rules:
      - Any comma (',') in the task name is treated as multi-action.
      - Any standalone " and " token is treated as multi-action.

    This intentionally avoids verb/grammar heuristics and keeps behavior fully deterministic.
    """
    lower = name.lower().strip()
    return ("," in lower) or (" and " in lower)
