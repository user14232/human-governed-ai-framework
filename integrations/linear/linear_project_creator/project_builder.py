"""
Orchestration layer for building a Linear project hierarchy from a ProjectModel.

Responsibilities:
  - Resolve label/state/user names to Linear IDs via LinearClient lookup methods.
  - Create the Linear project (with all metadata).
  - Create milestones, then epics → stories → tasks (strict top-down, sequential).
  - Compose full issue descriptions from description + acceptance_criteria + done_criteria.
  - After all issues are created, create issue relations for epic.blocks declarations.
  - After all issues are created, create issue relations for story.blocks declarations.
  - Accumulate and incrementally flush the mapping dict to disk.
  - Support dry-run mode: zero API calls, placeholder IDs returned.

Mapping structure returned:
  {
    "project": "<project_id>",
    "milestones": {"<name>": "<milestone_id>", ...},
    "epics": {"<epic_name>": "<issue_id>", ...},
    "stories": {"<story_name>": "<issue_id>", ...},
    "tasks": {"<task_name>": "<issue_id>", ...}
  }

Note on label strategy:
  Issue types (epic, story, task, bug, etc.) are applied as labels so that Linear's
  issue list can be filtered by type. All type labels plus any explicit labels from
  the YAML are resolved to IDs and combined into a single labelIds list per issue.

Note on relation strategy:
  Both epic.blocks and story.blocks are resolved in a second pass after the full
  issue tree is created. This allows cross-epic references (A in epic-1 blocks B in
  epic-2) to be resolved correctly. Unresolvable names are logged as warnings and
  skipped without failing the build.

  Order:
    1. Create all epics → stories → tasks (first pass).
    2. Create epic-level 'blocks' relations (second pass).
    3. Create story-level 'blocks' relations (third pass).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from linear_client import LinearAPIError, LinearClient
from models import EpicModel, ProjectModel, StoryModel, TaskModel

logger = logging.getLogger(__name__)

_DRY_RUN_PREFIX = "dry-run"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_project(
    project: ProjectModel,
    client: LinearClient,
    team_id: str,
    dry_run: bool,
    flush_path: Path | None = None,
) -> dict[str, Any]:
    """
    Create all Linear objects described by *project*.

    Args:
        project:    Fully parsed ProjectModel.
        client:     Authenticated LinearClient (not used in dry-run).
        team_id:    Linear team ID (embedded in client; passed explicitly for clarity).
        dry_run:    If True, no API calls are made; placeholder IDs returned.
        flush_path: Path to write the partial mapping JSON after each epic.

    Returns:
        Complete mapping dict.

    Raises:
        LinearAPIError: On any API failure (not raised in dry-run mode).
    """
    mapping: dict[str, Any] = {
        "project": "",
        "milestones": {},
        "epics": {},
        "stories": {},
        "tasks": {},
    }

    # ------------------------------------------------------------------
    # Pre-resolve project-level label IDs (single API call, cached)
    # ------------------------------------------------------------------
    issue_label_meta = _label_meta_map(project.issue_label_definitions)
    project_label_meta = _label_meta_map(project.project_label_definitions)

    project_label_ids = _resolve_project_labels(
        project.labels,
        client,
        dry_run,
        label_meta=project_label_meta,
    )

    # ------------------------------------------------------------------
    # Create project
    # ------------------------------------------------------------------
    project_id = _create_project(project, project_label_ids, client, dry_run)
    mapping["project"] = project_id
    _log_created("project", project.name, project_id, dry_run)

    # ------------------------------------------------------------------
    # Create milestones (must exist before epics/stories reference them)
    # ------------------------------------------------------------------
    milestone_name_to_id: dict[str, str] = {}
    for ms in project.milestones:
        ms_id = _create_milestone(ms.name, ms.description, ms.target_date, project_id, client, dry_run)
        milestone_name_to_id[ms.name] = ms_id
        mapping["milestones"][ms.name] = ms_id
        _log_created("milestone", ms.name, ms_id, dry_run)

    # ------------------------------------------------------------------
    # Create epics → stories → tasks
    # ------------------------------------------------------------------
    for epic in project.epics:
        try:
            epic_label_ids = _resolve_issue_labels(
                ("epic",) + epic.labels,
                client,
                dry_run,
                label_meta=issue_label_meta,
            )
            epic_milestone_id = milestone_name_to_id.get(epic.milestone) if epic.milestone else None
            epic_state_id = _resolve_state(epic.state, client, dry_run)
            epic_assignee_id = _resolve_user(epic.assignee, client, dry_run)

            epic_id = _create_epic(
                epic, project_id,
                label_ids=epic_label_ids,
                milestone_id=epic_milestone_id,
                state_id=epic_state_id,
                assignee_id=epic_assignee_id,
                client=client,
                dry_run=dry_run,
            )
            mapping["epics"][epic.name] = epic_id
            _log_created("epic", epic.name, epic_id, dry_run)

            for story in epic.stories:
                story_type_label = story.type or "story"
                story_label_ids = _resolve_issue_labels(
                    (story_type_label,) + story.labels,
                    client,
                    dry_run,
                    label_meta=issue_label_meta,
                )
                story_milestone_id = milestone_name_to_id.get(story.milestone) if story.milestone else None
                story_state_id = _resolve_state(story.state, client, dry_run)
                story_assignee_id = _resolve_user(story.assignee, client, dry_run)

                story_id = _create_story(
                    story, project_id, epic_id,
                    label_ids=story_label_ids,
                    milestone_id=story_milestone_id,
                    state_id=story_state_id,
                    assignee_id=story_assignee_id,
                    client=client,
                    dry_run=dry_run,
                )
                mapping["stories"][story.name] = story_id
                _log_created("story", story.name, story_id, dry_run)

                for task in story.tasks:
                    task_type_label = task.type or "task"
                    task_label_ids = _resolve_issue_labels(
                        (task_type_label,) + task.labels,
                        client,
                        dry_run,
                        label_meta=issue_label_meta,
                    )
                    task_state_id = _resolve_state(task.state, client, dry_run)
                    task_assignee_id = _resolve_user(task.assignee, client, dry_run)

                    task_id = _create_task(
                        task, project_id, story_id,
                        label_ids=task_label_ids,
                        state_id=task_state_id,
                        assignee_id=task_assignee_id,
                        client=client,
                        dry_run=dry_run,
                    )
                    mapping["tasks"][task.name] = task_id
                    _log_created("task", task.name, task_id, dry_run)

        except LinearAPIError:
            if flush_path is not None:
                _flush_mapping(mapping, flush_path)
            raise

        if flush_path is not None:
            _flush_mapping(mapping, flush_path)

    # ------------------------------------------------------------------
    # Step 4: Create epic-level 'blocks' relations — second pass.
    # All epics are in mapping["epics"]; resolve epic.blocks references.
    # ------------------------------------------------------------------
    _create_all_epic_relations(project, mapping["epics"], client, dry_run)

    # ------------------------------------------------------------------
    # Step 5: Create story-level 'blocks' relations — third pass.
    # All stories are in mapping["stories"]; resolve story.blocks references.
    # ------------------------------------------------------------------
    _create_all_story_relations(project, mapping["stories"], client, dry_run)

    return mapping


# ---------------------------------------------------------------------------
# Per-level creation helpers
# ---------------------------------------------------------------------------


def _create_project(
    project: ProjectModel,
    label_ids: list[str],
    client: LinearClient,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"{_DRY_RUN_PREFIX}:project:{_slug(project.name)}"
    return client.create_project(
        name=project.name,
        description=project.description,
        summary=project.summary,
        icon=project.icon,
        color=project.color,
        priority=project.priority,
        state=project.state,
        start_date=project.start_date,
        target_date=project.target_date,
        lead=project.lead,
        label_ids=label_ids or None,
    )


def _create_milestone(
    name: str,
    description: str,
    target_date: str | None,
    project_id: str,
    client: LinearClient,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"{_DRY_RUN_PREFIX}:milestone:{_slug(name)}"
    return client.create_milestone(
        name=name,
        project_id=project_id,
        description=description,
        target_date=target_date,
    )


def _create_epic(
    epic: EpicModel,
    project_id: str,
    *,
    label_ids: list[str],
    milestone_id: str | None,
    state_id: str | None,
    assignee_id: str | None,
    client: LinearClient,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"{_DRY_RUN_PREFIX}:epic:{_slug(epic.name)}"
    full_description = _compose_description(epic.description, epic.acceptance_criteria)
    return client.create_issue(
        title=epic.name,
        description=full_description,
        project_id=project_id,
        parent_id=None,
        priority=epic.priority,
        label_ids=label_ids or None,
        due_date=epic.due_date,
        assignee_id=assignee_id,
        state_id=state_id,
        milestone_id=milestone_id,
        links=[{"url": l.url, "title": l.title} for l in epic.links] or None,
    )


def _create_story(
    story: StoryModel,
    project_id: str,
    epic_id: str,
    *,
    label_ids: list[str],
    milestone_id: str | None,
    state_id: str | None,
    assignee_id: str | None,
    client: LinearClient,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"{_DRY_RUN_PREFIX}:story:{_slug(story.name)}"
    full_description = _compose_story_description(story)
    return client.create_issue(
        title=story.name,
        description=full_description,
        project_id=project_id,
        parent_id=epic_id,
        priority=story.priority,
        label_ids=label_ids or None,
        estimate=story.estimate,
        due_date=story.due_date,
        assignee_id=assignee_id,
        state_id=state_id,
        milestone_id=milestone_id,
        links=[{"url": l.url, "title": l.title} for l in story.links] or None,
    )


def _create_task(
    task: TaskModel,
    project_id: str,
    story_id: str,
    *,
    label_ids: list[str],
    state_id: str | None,
    assignee_id: str | None,
    client: LinearClient,
    dry_run: bool,
) -> str:
    if dry_run:
        return f"{_DRY_RUN_PREFIX}:task:{_slug(task.name)}"
    return client.create_issue(
        title=task.name,
        description=_compose_task_description(task),
        project_id=project_id,
        parent_id=story_id,
        priority=task.priority,
        label_ids=label_ids or None,
        estimate=task.estimate,
        due_date=task.due_date,
        assignee_id=assignee_id,
        state_id=state_id,
        links=[{"url": l.url, "title": l.title} for l in task.links] or None,
    )


# ---------------------------------------------------------------------------
# Relation helpers
# ---------------------------------------------------------------------------


def _create_all_epic_relations(
    project: ProjectModel,
    epic_name_to_id: dict[str, str],
    client: LinearClient,
    dry_run: bool,
) -> None:
    """
    Create 'blocks' relations in Linear for all epics that declare epic.blocks.

    Runs as a second pass after the full build so that all epic IDs are available.
    Unresolvable epic names are logged as warnings and skipped.
    """
    for epic in project.epics:
        if not epic.blocks:
            continue
        blocker_id = epic_name_to_id.get(epic.name)
        if blocker_id is None:
            logger.warning(
                "Cannot create relations for epic '%s': ID not in mapping.",
                epic.name,
            )
            continue
        for blocked_name in epic.blocks:
            blocked_id = epic_name_to_id.get(blocked_name)
            if blocked_id is None:
                logger.warning(
                    "Epic '%s' blocks '%s', but '%s' was not found in the "
                    "epic mapping. Skipping this relation.",
                    epic.name, blocked_name, blocked_name,
                )
                continue
            if dry_run:
                logger.info(
                    "[DRY-RUN] Would create relation: epic '%s' blocks epic '%s'.",
                    epic.name, blocked_name,
                )
            else:
                client.create_issue_relation(
                    issue_id=blocker_id,
                    related_issue_id=blocked_id,
                    relation_type="blocks",
                )


def _create_all_story_relations(
    project: ProjectModel,
    story_name_to_id: dict[str, str],
    client: LinearClient,
    dry_run: bool,
) -> None:
    """
    Create 'blocks' relations in Linear for all stories that declare story.blocks.

    Runs as a second pass after the full build so that cross-epic references
    (story in epic-1 blocks story in epic-2) are always resolvable.
    Unresolvable story names are logged as warnings and skipped.
    """
    for epic in project.epics:
        for story in epic.stories:
            if not story.blocks:
                continue
            blocker_id = story_name_to_id.get(story.name)
            if blocker_id is None:
                logger.warning(
                    "Cannot create relations for story '%s': ID not in mapping.",
                    story.name,
                )
                continue
            for blocked_name in story.blocks:
                blocked_id = story_name_to_id.get(blocked_name)
                if blocked_id is None:
                    logger.warning(
                        "Story '%s' blocks '%s', but '%s' was not found in the "
                        "story mapping. Skipping this relation.",
                        story.name, blocked_name, blocked_name,
                    )
                    continue
                if dry_run:
                    logger.info(
                        "[DRY-RUN] Would create relation: '%s' blocks '%s'.",
                        story.name, blocked_name,
                    )
                else:
                    client.create_issue_relation(
                        issue_id=blocker_id,
                        related_issue_id=blocked_id,
                        relation_type="blocks",
                    )


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def _resolve_issue_labels(
    names: tuple[str, ...] | list[str],
    client: LinearClient,
    dry_run: bool,
    *,
    label_meta: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    if dry_run or not names:
        return []
    return client.resolve_issue_label_ids(
        list(names),
        create_missing=True,
        label_meta=label_meta,
    )


def _resolve_project_labels(
    names: tuple[str, ...] | list[str],
    client: LinearClient,
    dry_run: bool,
    *,
    label_meta: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    if dry_run or not names:
        return []
    return client.resolve_project_label_ids(
        list(names),
        create_missing=True,
        label_meta=label_meta,
    )


def _resolve_state(name: str | None, client: LinearClient, dry_run: bool) -> str | None:
    if dry_run or name is None:
        return None
    resolved = client.resolve_state_id(name)
    if resolved is None:
        logger.warning("State '%s' not found in Linear workflow states — skipped.", name)
    return resolved


def _resolve_user(name: str | None, client: LinearClient, dry_run: bool) -> str | None:
    if dry_run or name is None:
        return None
    resolved = client.resolve_user_id(name)
    if resolved is None:
        logger.warning("User '%s' not found in Linear — assignee skipped.", name)
    return resolved


# ---------------------------------------------------------------------------
# Description composition
# ---------------------------------------------------------------------------


def _compose_description(description: str, acceptance_criteria: str | None) -> str:
    """
    Build a full Markdown issue body from description and acceptance criteria.

    The acceptance criteria block is appended under a '## Acceptance Criteria' heading.
    """
    if not acceptance_criteria:
        return description
    parts = [description] if description else []
    parts.append("## Acceptance Criteria\n\n" + acceptance_criteria.strip())
    return "\n\n".join(parts)


def _compose_story_description(story: StoryModel) -> str:
    """
    Build a full Markdown issue body for a story.

    Renders the base description, all populated DevOS planning fields under a
    dedicated section, and the acceptance criteria last — in that fixed order.
    Fields that are None (absent in YAML) are omitted entirely.
    """
    parts: list[str] = []

    if story.description:
        parts.append(story.description.strip())

    # DevOS planning fields — only emitted when present
    planning_sections: list[str] = []
    _devos_field = [
        ("Problem Statement", story.problem_statement),
        ("Scope", story.scope),
        ("Constraints", story.constraints),
        ("Architecture Context", story.architecture_context),
        ("Non-Goals", story.non_goals),
        ("Design Freedom", story.design_freedom),
    ]
    for heading, value in _devos_field:
        if value and value.strip():
            planning_sections.append(f"### {heading}\n\n{value.strip()}")

    if planning_sections:
        parts.append("## DevOS Planning Context\n\n" + "\n\n".join(planning_sections))

    if story.acceptance_criteria and story.acceptance_criteria.strip():
        parts.append("## Acceptance Criteria\n\n" + story.acceptance_criteria.strip())

    return "\n\n".join(parts)


def _compose_task_description(task: TaskModel) -> str:
    """
    Build a full Markdown issue body for a task.

    Renders the base description first, then appends the done_criteria block
    under a '## Done Criteria' heading when present.
    """
    parts: list[str] = []

    if task.description:
        parts.append(task.description.strip())

    if task.done_criteria and task.done_criteria.strip():
        parts.append("## Done Criteria\n\n" + task.done_criteria.strip())

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _log_created(level: str, name: str, obj_id: str, dry_run: bool) -> None:
    prefix = "[DRY-RUN] Would create" if dry_run else "Created"
    logger.info("%s %s '%s' → %s", prefix, level, name, obj_id)


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")[:60]


def _label_meta_map(definitions: tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    """
    Convert parsed label definitions into a lower-cased lookup map.
    """
    result: dict[str, dict[str, Any]] = {}
    for item in definitions:
        result[item.name.lower()] = {
            "description": item.description,
            "color": item.color,
            "is_group": item.is_group,
        }
    return result


def _flush_mapping(mapping: dict[str, Any], path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
        tmp.replace(path)
        logger.debug("Flushed partial mapping to %s", path)
    except OSError as exc:
        logger.warning("Could not flush mapping to %s: %s", path, exc)
