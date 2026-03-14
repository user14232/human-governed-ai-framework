"""
Provider interface for projecting DevOS planning artifacts to external tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .planning_models import EpicModel, StoryModel, TaskModel


class WorkItemProvider(ABC):
    @abstractmethod
    def create_epic(self, epic: EpicModel) -> str:
        """Create an epic in the external system and return its ID."""

    @abstractmethod
    def create_story(self, story: StoryModel) -> str:
        """Create a story in the external system and return its ID."""

    @abstractmethod
    def create_task(self, task: TaskModel) -> str:
        """Create a task in the external system and return its ID."""

