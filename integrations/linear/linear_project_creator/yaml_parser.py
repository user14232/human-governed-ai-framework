"""
YAML input parser for Linear project definitions.

Responsibilities:
  - Load YAML from disk.
  - Validate required fields; collect all errors before raising.
  - Parse all optional fields; return None for absent ones (never fill defaults silently).
  - Return a fully typed ProjectModel — no raw dicts escape this module.

Required / optional field summary:

  project:
    name          required
    description   required
    summary       optional
    icon          optional
    color         optional
    priority      optional  (integer 0–4)
    state         optional  (string)
    start_date    optional  (ISO date string)
    target_date   optional  (ISO date string)
    lead          optional  (name, email, or Linear ID)
    labels        optional  (list of strings)

  milestones[]:
    name          required
    description   optional
    target_date   optional

  epics[]:
    name                required
    description         required
    acceptance_criteria required  (Markdown string with verifiable done conditions)
    priority            optional
    labels              optional
    due_date            optional
    assignee            optional
    milestone           optional  (name of a milestone defined above)
    state               optional
    links[]             optional  → {url: required, title: required}
    blocks              optional  (list of epic names that cannot start until this epic is
                                   complete; resolved to Linear issue relations at build time)

  stories[]:
    name                required
    type                optional  (default: "story")
    description         required
    effort              required  (integer 1-5; see EFFORT SCALE in template.yaml)
    complexity          required  (integer 1-5; see COMPLEXITY SCALE in template.yaml)
    estimate            forbidden as manual override (computed as effort + complexity)
    priority            optional
    labels              optional
    due_date            optional
    assignee            optional
    milestone           optional
    state               optional
    acceptance_criteria optional  (Markdown string; linted for "- [ ]" checkbox format)
    links[]             optional
    problem_statement   optional  (DevOS: problem being solved; input to PLANNING stage)
    scope               optional  (DevOS: what is included; bounds the PLANNING output)
    constraints         optional  (DevOS: hard constraints enforced at ARCH_CHECK)
    architecture_context optional (DevOS: affected modules/contracts; used at ARCH_CHECK)
    non_goals           optional  (DevOS: explicit exclusions; prevents scope creep)
    design_freedom      optional  (DevOS: "high" | "restricted"; agent design latitude)
    blocks              optional  (list of story names that cannot start until this story
                                   is complete; resolved to Linear issue relations at build time)

  tasks[]:
    Bare string  → name only
    OR mapping:
      name          required
      type          optional  (default: "task")
      description   optional
      priority      optional
      labels        optional
      estimate      optional
      due_date      optional
      assignee      optional
      state         optional
      links[]       optional
      done_criteria optional  (explicit definition of done: output artifact, test result,
                               or observable state that proves the task is complete; linted
                               by TASK_MISSING_DOD when absent)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from models import (
    EpicModel,
    LabelDefinitionModel,
    LinkModel,
    MilestoneModel,
    ProjectModel,
    StoryModel,
    TaskModel,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_yaml(path: str) -> ProjectModel:
    """
    Parse a YAML project definition file and return a typed ProjectModel.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any structural validation errors are found.
        yaml.YAMLError: If the file is not valid YAML.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Input file not found: {resolved}")

    raw_text = resolved.read_text(encoding="utf-8")
    raw: Any = yaml.safe_load(raw_text)

    if not isinstance(raw, dict):
        raise ValueError(
            f"Top-level YAML structure must be a mapping, got {type(raw).__name__}."
        )

    errors: list[str] = []
    project = _parse_project(raw, errors)

    if errors:
        formatted = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(
            f"YAML validation failed with {len(errors)} error(s):\n{formatted}"
        )

    return project  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


def _parse_project(raw: dict[str, Any], errors: list[str]) -> ProjectModel | None:
    project_raw = raw.get("project")
    if not isinstance(project_raw, dict):
        errors.append("'project' key is missing or not a mapping.")
        return None

    name = _require_str(project_raw, "name", "project", errors)
    description = _require_str(project_raw, "description", "project", errors)

    milestones_raw = raw.get("milestones", [])
    if not isinstance(milestones_raw, list):
        errors.append("'milestones' must be a list.")
        milestones_raw = []

    milestones = tuple(
        _parse_milestone(m, idx, errors)
        for idx, m in enumerate(milestones_raw)
    )
    milestones = tuple(m for m in milestones if m is not None)  # type: ignore[assignment]

    epics_raw = raw.get("epics", [])
    if not isinstance(epics_raw, list):
        errors.append("'epics' must be a list.")
        epics_raw = []

    epics = tuple(
        _parse_epic(e, idx, errors)
        for idx, e in enumerate(epics_raw)
    )
    epics = tuple(e for e in epics if e is not None)  # type: ignore[assignment]

    label_defs_raw = raw.get("label_definitions", {})
    issue_label_definitions, project_label_definitions = _parse_label_definitions(
        label_defs_raw, errors
    )

    if name is None or description is None:
        return None

    return ProjectModel(
        name=name,
        description=description,
        summary=_opt_str(project_raw, "summary"),
        icon=_opt_str(project_raw, "icon"),
        color=_opt_str(project_raw, "color"),
        priority=_opt_int(project_raw, "priority", "project", errors),
        state=_opt_str(project_raw, "state"),
        start_date=_opt_str(project_raw, "start_date"),
        target_date=_opt_str(project_raw, "target_date"),
        lead=_opt_str(project_raw, "lead"),
        labels=_opt_str_list(project_raw, "labels", "project", errors),
        issue_label_definitions=issue_label_definitions,
        project_label_definitions=project_label_definitions,
        milestones=milestones,
        epics=epics,
    )


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


def _parse_milestone(raw: Any, idx: int, errors: list[str]) -> MilestoneModel | None:
    context = f"milestones[{idx}]"
    if not isinstance(raw, dict):
        errors.append(f"{context}: entry must be a mapping.")
        return None

    name = _require_str(raw, "name", context, errors)
    if name is None:
        return None

    description = _opt_str(raw, "description") or f"Milestone: {name}"

    return MilestoneModel(
        name=name,
        description=description,
        target_date=_opt_str(raw, "target_date"),
    )


# ---------------------------------------------------------------------------
# Epic
# ---------------------------------------------------------------------------


def _parse_epic(raw: Any, idx: int, errors: list[str]) -> EpicModel | None:
    context = f"epics[{idx}]"
    if not isinstance(raw, dict):
        errors.append(f"{context}: entry must be a mapping.")
        return None

    name = _require_str(raw, "name", context, errors)
    description = _require_str(raw, "description", context, errors)
    acceptance_criteria = _require_str(raw, "acceptance_criteria", context, errors)

    stories_raw = raw.get("stories", [])
    if not isinstance(stories_raw, list):
        errors.append(f"{context}: 'stories' must be a list.")
        stories_raw = []

    stories = tuple(
        _parse_story(s, idx, s_idx, errors)
        for s_idx, s in enumerate(stories_raw)
    )
    stories = tuple(s for s in stories if s is not None)  # type: ignore[assignment]

    if name is None or description is None or acceptance_criteria is None:
        return None

    return EpicModel(
        name=name,
        description=description,
        acceptance_criteria=acceptance_criteria,
        priority=_opt_int(raw, "priority", context, errors),
        labels=_opt_str_list(raw, "labels", context, errors),
        due_date=_opt_str(raw, "due_date"),
        assignee=_opt_str(raw, "assignee"),
        milestone=_opt_str(raw, "milestone"),
        state=_opt_str(raw, "state"),
        links=_parse_links(raw, context, errors),
        stories=stories,
        blocks=_opt_str_list(raw, "blocks", context, errors),
    )


# ---------------------------------------------------------------------------
# Story
# ---------------------------------------------------------------------------


_EFFORT_COMPLEXITY_MIN = 1
_EFFORT_COMPLEXITY_MAX = 5


def _parse_story(
    raw: Any,
    epic_idx: int,
    story_idx: int,
    errors: list[str],
) -> StoryModel | None:
    context = f"epics[{epic_idx}].stories[{story_idx}]"
    if not isinstance(raw, dict):
        errors.append(f"{context}: entry must be a mapping.")
        return None

    name = _require_str(raw, "name", context, errors)
    if name is None:
        return None

    description = _require_str(raw, "description", context, errors)
    if description is None:
        description = f"Story: {name}"

    effort = _require_bounded_int(
        raw, "effort", context, errors,
        lo=_EFFORT_COMPLEXITY_MIN, hi=_EFFORT_COMPLEXITY_MAX,
    )
    complexity = _require_bounded_int(
        raw, "complexity", context, errors,
        lo=_EFFORT_COMPLEXITY_MIN, hi=_EFFORT_COMPLEXITY_MAX,
    )

    if effort is not None and complexity is not None:
        computed_estimate = float(effort + complexity)
        explicit = _opt_float(raw, "estimate", context, errors)
        if explicit is not None and explicit != computed_estimate:
            errors.append(
                f"{context}: explicit 'estimate' ({explicit}) conflicts with computed value "
                f"effort ({effort}) + complexity ({complexity}) = {computed_estimate}. "
                f"Remove 'estimate' and let it be derived automatically."
            )
            estimate = None
        else:
            estimate = computed_estimate
    else:
        estimate = None

    tasks_raw = raw.get("tasks", [])
    if not isinstance(tasks_raw, list):
        errors.append(f"{context}: 'tasks' must be a list.")
        tasks_raw = []

    tasks = tuple(
        _parse_task(t, epic_idx, story_idx, t_idx, errors)
        for t_idx, t in enumerate(tasks_raw)
    )
    tasks = tuple(t for t in tasks if t is not None)  # type: ignore[assignment]

    if effort is None or complexity is None:
        return None

    return StoryModel(
        name=name,
        type=_opt_str(raw, "type") or "story",
        description=description,
        effort=effort,
        complexity=complexity,
        priority=_opt_int(raw, "priority", context, errors),
        labels=_opt_str_list(raw, "labels", context, errors),
        estimate=estimate,
        due_date=_opt_str(raw, "due_date"),
        assignee=_opt_str(raw, "assignee"),
        milestone=_opt_str(raw, "milestone"),
        state=_opt_str(raw, "state"),
        acceptance_criteria=_opt_str(raw, "acceptance_criteria"),
        links=_parse_links(raw, context, errors),
        tasks=tasks,
        problem_statement=_opt_str(raw, "problem_statement"),
        scope=_opt_str(raw, "scope"),
        constraints=_opt_str(raw, "constraints"),
        architecture_context=_opt_str(raw, "architecture_context"),
        non_goals=_opt_str(raw, "non_goals"),
        design_freedom=_opt_str(raw, "design_freedom"),
        blocks=_opt_str_list(raw, "blocks", context, errors),
    )


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


def _parse_task(
    raw: Any,
    epic_idx: int,
    story_idx: int,
    task_idx: int,
    errors: list[str],
) -> TaskModel | None:
    context = f"epics[{epic_idx}].stories[{story_idx}].tasks[{task_idx}]"

    if isinstance(raw, str):
        if not raw.strip():
            errors.append(f"{context}: task string must not be empty.")
            return None
        task_name = raw.strip()
        return TaskModel(
            name=task_name,
            type="task",
            description=f"Task: {task_name}",
            priority=None,
            labels=(),
            estimate=None,
            due_date=None,
            assignee=None,
            state=None,
            links=(),
            done_criteria=None,
        )

    if isinstance(raw, dict):
        name = _require_str(raw, "name", context, errors)
        if name is None:
            return None
        return TaskModel(
            name=name,
            type=_opt_str(raw, "type") or "task",
            description=_opt_str(raw, "description") or f"Task: {name}",
            priority=_opt_int(raw, "priority", context, errors),
            labels=_opt_str_list(raw, "labels", context, errors),
            estimate=_opt_float(raw, "estimate", context, errors),
            due_date=_opt_str(raw, "due_date"),
            assignee=_opt_str(raw, "assignee"),
            state=_opt_str(raw, "state"),
            links=_parse_links(raw, context, errors),
            done_criteria=_opt_str(raw, "done_criteria"),
        )

    errors.append(
        f"{context}: task must be a string or a mapping with 'name', "
        f"got {type(raw).__name__}."
    )
    return None


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


def _parse_links(raw: dict[str, Any], context: str, errors: list[str]) -> tuple[LinkModel, ...]:
    links_raw = raw.get("links", [])
    if not isinstance(links_raw, list):
        errors.append(f"{context}: 'links' must be a list.")
        return ()

    result: list[LinkModel] = []
    for i, link in enumerate(links_raw):
        link_ctx = f"{context}.links[{i}]"
        if not isinstance(link, dict):
            errors.append(f"{link_ctx}: must be a mapping with 'url' and 'title'.")
            continue
        url = _require_str(link, "url", link_ctx, errors)
        title = _require_str(link, "title", link_ctx, errors)
        if url and title:
            result.append(LinkModel(url=url, title=title))

    return tuple(result)


def _parse_label_definitions(
    raw: Any, errors: list[str]
) -> tuple[tuple[LabelDefinitionModel, ...], tuple[LabelDefinitionModel, ...]]:
    if raw is None:
        return (), ()
    if not isinstance(raw, dict):
        errors.append("'label_definitions' must be a mapping.")
        return (), ()

    issue_raw = raw.get("issue_labels", [])
    project_raw = raw.get("project_labels", [])

    issue_labels = _parse_label_definition_list(issue_raw, "label_definitions.issue_labels", errors)
    project_labels = _parse_label_definition_list(
        project_raw, "label_definitions.project_labels", errors
    )
    return issue_labels, project_labels


def _parse_label_definition_list(
    raw: Any, context: str, errors: list[str]
) -> tuple[LabelDefinitionModel, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        errors.append(f"{context} must be a list.")
        return ()

    labels: list[LabelDefinitionModel] = []
    for idx, entry in enumerate(raw):
        item_ctx = f"{context}[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{item_ctx} must be a mapping.")
            continue
        name = _require_str(entry, "name", item_ctx, errors)
        if name is None:
            continue
        description = _opt_str(entry, "description") or f"Label: {name}"
        color = _opt_str(entry, "color")
        is_group = _opt_bool(entry, "is_group", item_ctx, errors) or False
        labels.append(
            LabelDefinitionModel(
                name=name,
                description=description,
                color=color,
                is_group=is_group,
            )
        )

    return tuple(labels)


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------


def _require_str(
    mapping: dict[str, Any], key: str, context: str, errors: list[str]
) -> str | None:
    value = mapping.get(key)
    if value is None:
        errors.append(f"{context}: required field '{key}' is missing.")
        return None
    if not isinstance(value, str):
        errors.append(
            f"{context}: field '{key}' must be a string, got {type(value).__name__}."
        )
        return None
    if not value.strip():
        errors.append(f"{context}: field '{key}' must not be empty.")
        return None
    return value


def _opt_str(mapping: dict[str, Any], key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    return str(value)


def _opt_int(
    mapping: dict[str, Any], key: str, context: str, errors: list[str]
) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(f"{context}: field '{key}' must be an integer, not a boolean.")
        return None
    if isinstance(value, int):
        return value
    errors.append(
        f"{context}: field '{key}' must be an integer, got {type(value).__name__}."
    )
    return None


def _opt_float(
    mapping: dict[str, Any], key: str, context: str, errors: list[str]
) -> float | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(f"{context}: field '{key}' must be numeric, not a boolean.")
        return None
    if isinstance(value, (int, float)):
        return float(value)
    errors.append(
        f"{context}: field '{key}' must be numeric, got {type(value).__name__}."
    )
    return None


def _opt_str_list(
    mapping: dict[str, Any], key: str, context: str, errors: list[str]
) -> tuple[str, ...]:
    value = mapping.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        errors.append(f"{context}: field '{key}' must be a list of strings.")
        return ()
    result: list[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"{context}: {key}[{i}] must be a string, got {type(item).__name__}."
            )
        elif item.strip():
            result.append(item.strip())
    return tuple(result)


def _opt_bool(
    mapping: dict[str, Any], key: str, context: str, errors: list[str]
) -> bool | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    errors.append(
        f"{context}: field '{key}' must be a boolean, got {type(value).__name__}."
    )
    return None


def _require_bounded_int(
    mapping: dict[str, Any],
    key: str,
    context: str,
    errors: list[str],
    lo: int,
    hi: int,
) -> int | None:
    """
    Require an integer field in the inclusive range [lo, hi].

    Returns the value if valid, appends to errors and returns None otherwise.
    """
    value = mapping.get(key)
    if value is None:
        errors.append(
            f"{context}: required field '{key}' is missing "
            f"(integer {lo}-{hi} required)."
        )
        return None
    if isinstance(value, bool):
        errors.append(
            f"{context}: field '{key}' must be an integer {lo}-{hi}, not a boolean."
        )
        return None
    if not isinstance(value, int):
        errors.append(
            f"{context}: field '{key}' must be an integer {lo}-{hi}, "
            f"got {type(value).__name__}."
        )
        return None
    if not (lo <= value <= hi):
        errors.append(
            f"{context}: field '{key}' must be between {lo} and {hi} inclusive, "
            f"got {value}."
        )
        return None
    return value
