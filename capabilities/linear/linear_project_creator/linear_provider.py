"""
Linear adapter for DevOS planning projection.

This module keeps Linear-specific side effects behind a provider interface so
the core planning engine remains independent from external tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .linear_client import LinearClient
    from .models import EpicModel, ProjectModel, StoryModel, TaskModel
    from .planning_engine import DEFAULT_PROJECT_PLAN_PATH, PlanningEngine
    from .project_builder import BuildStats, build_project
    from .work_item_provider import WorkItemProvider
except ImportError:  # pragma: no cover - script execution fallback
    from linear_client import LinearClient
    from models import EpicModel, ProjectModel, StoryModel, TaskModel
    from planning_engine import DEFAULT_PROJECT_PLAN_PATH, PlanningEngine
    from project_builder import BuildStats, build_project
    from work_item_provider import WorkItemProvider


class LinearProvider(WorkItemProvider):
    """
    Linear implementation of the WorkItemProvider interface.

    For full project projection, this adapter delegates to the existing
    deterministic build orchestration (`build_project`) to preserve behavior.
    """

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
        """
        Project a validated DevOS plan into Linear.
        """
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
        """
        Load a DevOS plan artifact, validate it, and sync it to Linear.
        """
        planning_engine = PlanningEngine()
        validation_result = planning_engine.load_and_validate(
            plan_path=plan_path,
            lint_mode=lint_mode,
        )
        return self.sync_project(validation_result.project, flush_path=flush_path)

    # ------------------------------------------------------------------
    # WorkItemProvider contract
    # ------------------------------------------------------------------
    #
    # NOTE:
    # Linear issue creation for stories/tasks requires parent context. The
    # canonical projection path should use sync_project(), which provides the
    # complete hierarchy and deterministic ordering guarantees.
    #
    # These methods are implemented to satisfy the adapter interface for future
    # composition patterns.

    def create_epic(self, epic: EpicModel) -> str:
        raise NotImplementedError(
            "Use sync_project() for deterministic hierarchical sync to Linear."
        )

    def create_story(self, story: StoryModel) -> str:
        raise NotImplementedError(
            "Use sync_project() for deterministic hierarchical sync to Linear."
        )

    def create_task(self, task: TaskModel) -> str:
        raise NotImplementedError(
            "Use sync_project() for deterministic hierarchical sync to Linear."
        )

