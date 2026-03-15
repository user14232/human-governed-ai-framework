"""
Deterministic semantic quality linter for DevOS planning artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .planning_models import EpicModel, ProjectModel, StoryModel, TaskModel


@dataclass(frozen=True)
class LintViolation:
    context: str
    rule_id: str
    message: str


def lint_project(project: ProjectModel) -> list[LintViolation]:
    violations: list[LintViolation] = []
    all_epic_names: frozenset[str] = frozenset(epic.name for epic in project.epics)
    all_story_names: frozenset[str] = frozenset(
        story.name for epic in project.epics for story in epic.stories
    )
    project_defines_milestones = len(project.milestones) > 0
    epic_blocks_graph: dict[str, tuple[str, ...]] = {
        epic.name: epic.blocks for epic in project.epics if epic.blocks
    }
    story_blocks_graph: dict[str, tuple[str, ...]] = {
        story.name: story.blocks
        for epic in project.epics
        for story in epic.stories
        if story.blocks
    }

    _lint_project_level(project, violations)
    _lint_epic_blocks_cycle(epic_blocks_graph, all_epic_names, violations)
    _lint_story_blocks_cycle(story_blocks_graph, all_story_names, violations)

    for epic_idx, epic in enumerate(project.epics):
        _lint_epic(
            epic,
            epic_idx,
            all_epic_names=all_epic_names,
            all_story_names=all_story_names,
            project_defines_milestones=project_defines_milestones,
            violations=violations,
        )

    return violations


def _lint_project_level(project: ProjectModel, violations: list[LintViolation]) -> None:
    context = f"project ({project.name!r})"
    if len(project.epics) > 1:
        any_epic_has_blocks = any(epic.blocks for epic in project.epics)
        if not any_epic_has_blocks:
            violations.append(
                LintViolation(
                    context=context,
                    rule_id="PROJECT_NO_EPIC_DEPS",
                    message=(
                        f"Project has {len(project.epics)} epics but no epic declares a "
                        "'blocks' dependency."
                    ),
                )
            )


def _find_cycle_in_blocks_graph(
    name_to_blocks: dict[str, tuple[str, ...]],
    all_known_names: frozenset[str],
) -> list[str] | None:
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def _dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in name_to_blocks.get(node, ()):
            if neighbor not in all_known_names:
                continue
            if neighbor not in visited:
                if _dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                path.append(neighbor)
                return True
        path.pop()
        rec_stack.discard(node)
        return False

    for node in sorted(all_known_names):
        if node not in visited and _dfs(node):
            return path
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
        violations.append(
            LintViolation(
                context="project (epic blocks graph)",
                rule_id="EPIC_BLOCKS_CYCLE",
                message=f"Circular dependency detected in epic blocks: {' -> '.join(cycle)}.",
            )
        )


def _lint_story_blocks_cycle(
    story_blocks_graph: dict[str, tuple[str, ...]],
    all_story_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    if not story_blocks_graph:
        return
    cycle = _find_cycle_in_blocks_graph(story_blocks_graph, all_story_names)
    if cycle is not None:
        violations.append(
            LintViolation(
                context="project (story blocks graph)",
                rule_id="STORY_BLOCKS_CYCLE",
                message=f"Circular dependency detected in story blocks: {' -> '.join(cycle)}.",
            )
        )


_EPIC_MIN_STORIES = 2
_EPIC_MAX_STORIES = 10
_EPIC_DESC_MIN_WORDS = 20
_STORY_MIN_TASKS = 2
_STORY_MAX_TASKS = 7
_STORY_DESIGN_FREEDOM_VALUES = frozenset({"high", "restricted"})
_TEST_TASK_KEYWORDS = frozenset({"test", "verify", "validate", "spec", "check"})
_TASK_TYPE_VALUES = frozenset({"implementation", "verification"})

_STORY_REQUIRED_DEVOS_FIELDS: tuple[tuple[str, str], ...] = (
    ("problem_statement", "Problem Statement"),
    ("scope", "Scope"),
    ("constraints", "Constraints"),
    ("architecture_context", "Architecture Context"),
    ("non_goals", "Non-Goals"),
)


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
        violations.append(
            LintViolation(
                context=context,
                rule_id="EPIC_MIN_STORIES",
                message=f"Epic contains {story_count} story/stories; minimum is {_EPIC_MIN_STORIES}.",
            )
        )
    if story_count > _EPIC_MAX_STORIES:
        violations.append(
            LintViolation(
                context=context,
                rule_id="EPIC_MAX_STORIES",
                message=f"Epic contains {story_count} stories; maximum is {_EPIC_MAX_STORIES}.",
            )
        )

    word_count = len(epic.description.split()) if epic.description else 0
    if word_count < _EPIC_DESC_MIN_WORDS:
        violations.append(
            LintViolation(
                context=context,
                rule_id="EPIC_DESC_MIN_WORDS",
                message=f"Epic description contains {word_count} word(s); minimum is {_EPIC_DESC_MIN_WORDS}.",
            )
        )
    if "- [ ]" not in epic.acceptance_criteria:
        violations.append(
            LintViolation(
                context=context,
                rule_id="EPIC_AC_CHECKBOX_FORMAT",
                message="Epic acceptance criteria must include '- [ ]' checkbox items.",
            )
        )
    if project_defines_milestones and epic.milestone is None:
        violations.append(
            LintViolation(
                context=context,
                rule_id="EPIC_MISSING_MILESTONE",
                message="Epic has no milestone but project defines milestones.",
            )
        )
    for blocked_name in epic.blocks:
        if blocked_name == epic.name or blocked_name not in all_epic_names:
            violations.append(
                LintViolation(
                    context=context,
                    rule_id="EPIC_BLOCKS_VALID",
                    message=f"Epic 'blocks' reference '{blocked_name}' is invalid.",
                )
            )

    for story_idx, story in enumerate(epic.stories):
        _lint_story(story, epic_idx, story_idx, all_story_names, violations)


def _lint_story(
    story: StoryModel,
    epic_idx: int,
    story_idx: int,
    all_story_names: frozenset[str],
    violations: list[LintViolation],
) -> None:
    context = f"epics[{epic_idx}].stories[{story_idx}] ({story.name!r})"

    for field_name, _label in _STORY_REQUIRED_DEVOS_FIELDS:
        value = getattr(story, field_name, None)
        if not value or not str(value).strip():
            violations.append(
                LintViolation(
                    context=context,
                    rule_id="STORY_REQUIRED_FIELD",
                    message=f"Story is missing required DevOS planning field '{field_name}'.",
                )
            )

    if not story.design_freedom or not story.design_freedom.strip():
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_DESIGN_FREEDOM_REQUIRED",
                message="Story is missing required field 'design_freedom'.",
            )
        )
    elif story.design_freedom.strip().lower() not in _STORY_DESIGN_FREEDOM_VALUES:
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_DESIGN_FREEDOM",
                message=f"Invalid design_freedom value '{story.design_freedom}'.",
            )
        )

    if not story.acceptance_criteria or not story.acceptance_criteria.strip():
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_AC_REQUIRED",
                message="Story must include acceptance_criteria.",
            )
        )
    elif "- [ ]" not in story.acceptance_criteria:
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_AC_CHECKBOX_FORMAT",
                message="Story acceptance_criteria must include '- [ ]' checkbox items.",
            )
        )

    task_count = len(story.tasks)
    if task_count < _STORY_MIN_TASKS:
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_TASK_MIN",
                message=f"Story contains {task_count} task(s); minimum is {_STORY_MIN_TASKS}.",
            )
        )
    if task_count > _STORY_MAX_TASKS:
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_TASK_MAX",
                message=f"Story contains {task_count} tasks; maximum is {_STORY_MAX_TASKS}.",
            )
        )
    if task_count >= _STORY_MIN_TASKS and not _story_has_test_task(story):
        violations.append(
            LintViolation(
                context=context,
                rule_id="STORY_MISSING_TEST_TASK",
                message="Story must include at least one verification test task.",
            )
        )

    for blocked_name in story.blocks:
        if blocked_name == story.name or blocked_name not in all_story_names:
            violations.append(
                LintViolation(
                    context=context,
                    rule_id="STORY_BLOCKS_VALID",
                    message=f"Story 'blocks' reference '{blocked_name}' is invalid.",
                )
            )

    for task_idx, task in enumerate(story.tasks):
        _lint_task(task, epic_idx, story_idx, task_idx, violations)


def _story_has_test_task(story: StoryModel) -> bool:
    for task in story.tasks:
        if task.task_type is not None and task.task_type.strip().lower() == "verification":
            return True
        lower_name = task.name.lower()
        if any(kw in lower_name for kw in _TEST_TASK_KEYWORDS):
            return True
    return False


def _lint_task(
    task: TaskModel,
    epic_idx: int,
    story_idx: int,
    task_idx: int,
    violations: list[LintViolation],
) -> None:
    context = f"epics[{epic_idx}].stories[{story_idx}].tasks[{task_idx}] ({task.name!r})"
    lower = task.name.lower().strip()
    if ("," in lower) or (" and " in lower):
        violations.append(
            LintViolation(
                context=context,
                rule_id="TASK_MULTI_ACTION",
                message="Task name appears to combine multiple actions.",
            )
        )
    if not task.done_criteria or not task.done_criteria.strip():
        violations.append(
            LintViolation(
                context=context,
                rule_id="TASK_MISSING_DOD",
                message="Task is missing done_criteria.",
            )
        )
    if task.task_type is not None:
        normalized = task.task_type.strip().lower()
        if normalized not in _TASK_TYPE_VALUES:
            violations.append(
                LintViolation(
                    context=context,
                    rule_id="TASK_TYPE_VALID",
                    message=f"Invalid task_type '{task.task_type}'.",
                )
            )

