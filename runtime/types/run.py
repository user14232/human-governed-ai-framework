from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from runtime.types.workflow import WorkflowDefinition

RunId = str


@dataclass(frozen=True)
class RunContext:
    run_id: RunId
    project_root: Path
    run_dir: Path
    artifacts_dir: Path
    workflow_def: WorkflowDefinition
    current_state: str


@dataclass(frozen=True)
class RunState:
    run_id: RunId
    current_state: str
    is_terminal: bool
    last_event_id: str | None


TERMINAL_STATES: frozenset[str] = frozenset(
    {
        "ACCEPTED",
        "ACCEPTED_WITH_DEBT",
        "FAILED",
        "HUMAN_DECISION",
        "RELEASED",
        "RELEASE_FAILED",
    }
)

