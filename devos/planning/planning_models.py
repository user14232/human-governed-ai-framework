"""
Pure value objects for the DevOS planning hierarchy.

No behaviour. No defaults. No mutable state.
All objects are frozen and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkModel:
    url: str
    title: str


@dataclass(frozen=True)
class LabelDefinitionModel:
    name: str
    description: str
    color: str | None
    is_group: bool


@dataclass(frozen=True)
class MilestoneModel:
    name: str
    description: str
    target_date: str | None


@dataclass(frozen=True)
class ProjectModel:
    name: str
    description: str
    summary: str | None
    icon: str | None
    color: str | None
    priority: int | None
    state: str | None
    start_date: str | None
    target_date: str | None
    lead: str | None
    labels: tuple[str, ...]
    issue_label_definitions: tuple[LabelDefinitionModel, ...]
    project_label_definitions: tuple[LabelDefinitionModel, ...]
    milestones: tuple[MilestoneModel, ...]
    epics: tuple["EpicModel", ...]


@dataclass(frozen=True)
class TaskModel:
    name: str
    type: str
    task_type: str | None
    description: str
    priority: int | None
    labels: tuple[str, ...]
    estimate: float | None
    due_date: str | None
    assignee: str | None
    state: str | None
    links: tuple[LinkModel, ...]
    done_criteria: str | None


@dataclass(frozen=True)
class StoryModel:
    name: str
    type: str
    description: str
    effort: int
    complexity: int
    priority: int | None
    labels: tuple[str, ...]
    estimate: float | None
    due_date: str | None
    assignee: str | None
    milestone: str | None
    state: str | None
    acceptance_criteria: str | None
    links: tuple[LinkModel, ...]
    tasks: tuple[TaskModel, ...]
    problem_statement: str | None
    scope: str | None
    constraints: str | None
    architecture_context: str | None
    non_goals: str | None
    design_freedom: str | None
    blocks: tuple[str, ...]


@dataclass(frozen=True)
class EpicModel:
    name: str
    description: str
    acceptance_criteria: str
    priority: int | None
    labels: tuple[str, ...]
    due_date: str | None
    assignee: str | None
    milestone: str | None
    state: str | None
    links: tuple[LinkModel, ...]
    stories: tuple[StoryModel, ...]
    blocks: tuple[str, ...]

