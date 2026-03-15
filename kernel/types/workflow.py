from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequiresBlock:
    inputs_present: bool | None
    artifacts: tuple[str, ...]
    human_approval: tuple[str, ...]
    conditions: dict[str, str]


@dataclass(frozen=True)
class Transition:
    from_state: str
    to_state: str
    requires: RequiresBlock
    notes: str | None


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    version: str
    states: tuple[str, ...]
    transitions: tuple[Transition, ...]
    artifacts_used: tuple[str, ...]

