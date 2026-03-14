from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from shutil import copyfile

from runtime.engine.workflow_engine import StateReconstructionError as WorkflowStateReconstructionError
from runtime.engine.workflow_engine import WorkflowEngine
from runtime.events.event_system import EventSystem
from runtime.framework.schema_loader import ParseError as SchemaParseError
from runtime.framework.schema_loader import load_all_schemas
from runtime.framework.workflow_loader import load_workflow
from runtime.knowledge.extraction_hooks import check_triggers, log_trigger
from runtime.store.run_store import (
    create_run_directory,
    decision_log_path,
    list_run_ids,
    run_directory,
    run_metrics_path,
)
from runtime.types.run import RunContext, TERMINAL_STATES


class MissingInputError(FileNotFoundError):
    """Raised when required input files are missing."""


class InvalidTerminalStateError(ValueError):
    """Raised when terminal declaration is called with a non-terminal state."""


class StateReconstructionError(RuntimeError):
    """Raised when run state cannot be reconstructed deterministically."""


class RunEngine:
    def __init__(self, event_system: EventSystem | None = None) -> None:
        self._events = event_system or EventSystem()

    def initialize_run(
        self,
        project_root: Path,
        change_intent_path: Path,
        workflow_name: str = "default_workflow",
    ) -> RunContext:
        if not change_intent_path.is_file():
            raise MissingInputError(f"Missing change intent file: {change_intent_path}")

        workflow_path = project_root / "workflow" / f"{workflow_name}.yaml"
        workflow_def = load_workflow(workflow_path)

        run_id = self._next_run_id(project_root)
        run_dir = create_run_directory(project_root, run_id)
        artifacts_dir = run_dir / "artifacts"
        copyfile(change_intent_path, artifacts_dir / "change_intent.yaml")
        metrics_path = run_metrics_path(run_dir)

        initial_state = workflow_def.states[0]
        ctx = RunContext(
            run_id=run_id,
            project_root=project_root.resolve(),
            run_dir=run_dir.resolve(),
            artifacts_dir=artifacts_dir.resolve(),
            workflow_def=workflow_def,
            current_state=initial_state,
        )
        self._events.emit(
            run_metrics_path=metrics_path,
            run_id=ctx.run_id,
            event_type=self._events_event_type("run.started"),
            producer="runtime",
            workflow_state=initial_state,
            causation_event_id=None,
            payload={
                "workflow_id": workflow_def.workflow_id,
                "change_intent_id": "unknown",
                "project_inputs": [],
            },
        )
        return ctx

    def resume_run(
        self,
        project_root: Path,
        run_id: str,
        workflow_name: str = "default_workflow",
    ) -> RunContext:
        run_dir = run_directory(project_root, run_id)
        artifacts_dir = run_dir / "artifacts"
        workflow_path = project_root / "workflow" / f"{workflow_name}.yaml"
        workflow_def = load_workflow(workflow_path)
        try:
            schemas = load_all_schemas(project_root / "artifacts" / "schemas")
        except SchemaParseError:
            schemas = {}
        wf_engine = WorkflowEngine(workflow_def)
        try:
            state = wf_engine.reconstruct_state(
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path(run_dir),
                schemas=schemas,
                run_metrics_path=run_metrics_path(run_dir),
            )
        except WorkflowStateReconstructionError as exc:
            raise StateReconstructionError(str(exc)) from exc

        ctx = RunContext(
            run_id=run_id,
            project_root=project_root.resolve(),
            run_dir=run_dir.resolve(),
            artifacts_dir=artifacts_dir.resolve(),
            workflow_def=workflow_def,
            current_state=state,
        )
        self._events.emit(
            run_metrics_path=run_metrics_path(run_dir),
            run_id=ctx.run_id,
            event_type=self._events_event_type("run.resumed"),
            producer="runtime",
            workflow_state=ctx.current_state,
            causation_event_id=None,
            payload={"resumed": True},
        )
        return ctx

    def declare_terminal(
        self,
        ctx: RunContext,
        terminal_state: str,
    ) -> None:
        if terminal_state not in TERMINAL_STATES:
            raise InvalidTerminalStateError(
                f"State '{terminal_state}' is not a valid terminal state."
            )
        metrics_path = run_metrics_path(ctx.run_dir)
        completed_event = self._events.emit(
            run_metrics_path=metrics_path,
            run_id=ctx.run_id,
            event_type=self._events_event_type("run.completed"),
            producer="runtime",
            workflow_state=terminal_state,
            causation_event_id=None,
            payload={"terminal_state": terminal_state, "duration_seconds": 0.0},
        )
        trigger = check_triggers(terminal_state)
        if trigger is not None:
            terminal_ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=terminal_state,
            )
            log_trigger(
                ctx=terminal_ctx,
                trigger=trigger,
                event_system=self._events,
                run_metrics_path=metrics_path,
                causation_event_id=completed_event.event_id,
            )

    def _next_run_id(self, project_root: Path) -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        existing = [rid for rid in list_run_ids(project_root) if rid.startswith(f"RUN-{date_part}-")]
        suffix = len(existing) + 1
        return f"RUN-{date_part}-{suffix:04d}"

    @staticmethod
    def _events_event_type(name: str):
        from runtime.types.event import EventType

        mapping = {
            "run.started": EventType.RUN_STARTED,
            "run.resumed": EventType.RUN_RESUMED,
            "run.completed": EventType.RUN_COMPLETED,
        }
        return mapping[name]

