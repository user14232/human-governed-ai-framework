from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from runtime.engine.gate_evaluator import GateEvaluator as DefaultGateEvaluator
from runtime.types.artifact import ArtifactSchema
from runtime.types.gate import CheckResult, GateResult
from runtime.types.run import RunContext
from runtime.types.workflow import Transition, WorkflowDefinition


class NoEligibleTransitionsError(RuntimeError):
    """Raised when a state has no outbound transitions in the workflow definition."""


class StateReconstructionError(RuntimeError):
    """Raised when workflow state cannot be reconstructed deterministically."""


class GateEvaluator(Protocol):
    def evaluate(
        self,
        transition: Transition,
        project_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        """Evaluate gate conditions for one transition."""


@dataclass(frozen=True)
class AdvanceResult:
    transitioned: bool
    new_state: str | None
    blocked_at: str | None
    gate_result: GateResult | None


class WorkflowEngine:
    def __init__(self, workflow_def: WorkflowDefinition) -> None:
        self._workflow = workflow_def

    def get_eligible_transitions(self, current_state: str) -> list[Transition]:
        return [t for t in self._workflow.transitions if t.from_state == current_state]

    def advance(
        self,
        ctx: RunContext,
        evaluator: GateEvaluator,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> AdvanceResult:
        eligible = self.get_eligible_transitions(ctx.current_state)
        if not eligible:
            raise NoEligibleTransitionsError(
                f"No transitions available from state '{ctx.current_state}'."
            )

        for transition in eligible:
            gate_result = evaluator.evaluate(
                transition=transition,
                project_root=ctx.project_root,
                artifacts_dir=ctx.artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=schemas,
            )
            if gate_result.result == CheckResult.PASS:
                return AdvanceResult(
                    transitioned=True,
                    new_state=transition.to_state,
                    blocked_at=None,
                    gate_result=gate_result,
                )
            return AdvanceResult(
                transitioned=False,
                new_state=None,
                blocked_at=ctx.current_state,
                gate_result=gate_result,
            )

        raise NoEligibleTransitionsError(
            f"No transition result produced from state '{ctx.current_state}'."
        )

    def reconstruct_state(
        self,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
        run_metrics_path: Path | None,
    ) -> str:
        # Primary reconstruction path: explicit transition completion event.
        if run_metrics_path and run_metrics_path.is_file():
            from_metrics = _state_from_metrics(run_metrics_path)
            if from_metrics is not None:
                return from_metrics

        # Deterministic fallback: traverse transitions from INIT in declared order
        # and advance only when gate checks pass.
        state = "INIT"
        evaluator = DefaultGateEvaluator()
        # Infer project root from canonical path runs/<run_id>/artifacts.
        # artifacts_dir.parent -> run_dir, artifacts_dir.parent.parent -> runs,
        # artifacts_dir.parent.parent.parent -> project_root.
        project_root = artifacts_dir.parent.parent.parent
        max_hops = max(len(self._workflow.transitions), 1)
        hops = 0
        while hops < max_hops:
            hops += 1
            eligible = self.get_eligible_transitions(state)
            if not eligible:
                return state
            transitioned = False
            for transition in eligible:
                gate_result = evaluator.evaluate(
                    transition=transition,
                    project_root=project_root,
                    artifacts_dir=artifacts_dir,
                    decision_log_path=decision_log_path,
                    schemas=schemas,
                )
                if gate_result.result == CheckResult.PASS:
                    state = transition.to_state
                    transitioned = True
                    break
                # First fail blocks progression from this state.
                return state
            if not transitioned:
                return state

        raise StateReconstructionError("State reconstruction exceeded deterministic hop limit.")


def _state_from_metrics(run_metrics_path: Path) -> str | None:
    try:
        payload = json.loads(run_metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateReconstructionError(
            f"Invalid run metrics JSON at {run_metrics_path}."
        ) from exc
    events = payload.get("events", [])
    if not isinstance(events, list):
        raise StateReconstructionError("run_metrics.json 'events' must be a list.")

    last_to_state: str | None = None
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("event_type") != "workflow.transition_completed":
            continue
        event_payload = event.get("payload", {})
        if not isinstance(event_payload, dict):
            continue
        to_state = event_payload.get("to_state")
        if isinstance(to_state, str) and to_state:
            last_to_state = to_state
    return last_to_state

