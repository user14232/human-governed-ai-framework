"""
Linear WorkItemProvider implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devos.planning.planning_engine import DEFAULT_PROJECT_PLAN_PATH, PlanningEngine
from devos.planning.planning_models import EpicModel, ProjectModel, StoryModel, TaskModel
from devos.planning.work_item_provider import WorkItemProvider

from .linear_client import LinearClient
from .project_builder import BuildStats, build_project


class LinearProvider(WorkItemProvider):
    def __init__(self, client: LinearClient, team_id: str, *, dry_run: bool = False) -> None:
        self._client = client
        self._team_id = team_id
        self._dry_run = dry_run

    def sync_project(
        self,
        project: ProjectModel,
        *,
        flush_path: Path | None = None,
    ) -> tuple[dict[str, Any], BuildStats]:
        return build_project(
            project=project,
            client=self._client,
            team_id=self._team_id,
            dry_run=self._dry_run,
            flush_path=flush_path,
        )

    def sync_from_plan(
        self,
        plan_path: str | Path = DEFAULT_PROJECT_PLAN_PATH,
        *,
        lint_mode: str = "enforce",
        flush_path: Path | None = None,
    ) -> tuple[dict[str, Any], BuildStats]:
        planning_engine = PlanningEngine()
        validation_result = planning_engine.load_and_validate(plan_path=plan_path, lint_mode=lint_mode)
        return self.sync_project(validation_result.project, flush_path=flush_path)

    def create_epic(self, epic: EpicModel) -> str:
        raise NotImplementedError("Use sync_project() for deterministic hierarchical sync to Linear.")

    def create_story(self, story: StoryModel) -> str:
        raise NotImplementedError("Use sync_project() for deterministic hierarchical sync to Linear.")

    def create_task(self, task: TaskModel) -> str:
        raise NotImplementedError("Use sync_project() for deterministic hierarchical sync to Linear.")

