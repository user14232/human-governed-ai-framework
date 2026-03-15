from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from kernel.engine.gate_evaluator import GateEvaluator as DefaultGateEvaluator
from kernel.events.event_system import EventSystem
from kernel.store.run_store import run_metrics_path
from kernel.types.artifact import ArtifactSchema
from kernel.types.gate import CheckResult, CheckType, GateCheckDetail, GateResult
from kernel.types.event import EventType
from kernel.types.run import RunContext
from kernel.types.workflow import Transition, WorkflowDefinition


class NoEligibleTransitionsError(RuntimeError):
    """Raised when a state has no outbound transitions in the workflow definition."""


class StateReconstructionError(RuntimeError):
    """Raised when workflow state cannot be reconstructed deterministically."""


class GateEvaluator(Protocol):
    def evaluate(
        self,
        transition: Transition,
        project_inputs_root: Path,
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
    def __init__(
        self,
        workflow_def: WorkflowDefinition,
        event_system: EventSystem | None = None,
    ) -> None:
        self._workflow = workflow_def
        self._events = event_system or EventSystem()

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
        metrics_path = run_metrics_path(ctx.run_dir)
        last_event_id = self._events.last_event_id(metrics_path)
        last_gate_result: GateResult | None = None
        attempted_to_states: list[str] = []

        for transition in eligible:
            gate_result = evaluator.evaluate(
                transition=transition,
                project_inputs_root=ctx.project_inputs_root or ctx.project_root,
                artifacts_dir=ctx.artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=schemas,
            )
            checked_event = self._events.emit(
                run_metrics_path=metrics_path,
                run_id=ctx.run_id,
                event_type=EventType.WORKFLOW_TRANSITION_CHECKED,
                producer="runtime",
                workflow_state=ctx.current_state,
                causation_event_id=last_event_id,
                payload={
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "result": gate_result.result.value,
                    "checks": [
                        {
                            "check_type": check.check_type.value,
                            "subject": check.subject,
                            "result": check.result.value,
                            "detail": check.detail,
                        }
                        for check in gate_result.checks
                    ],
                },
            )
            last_event_id = checked_event.event_id
            last_gate_result = gate_result
            attempted_to_states.append(transition.to_state)
            if gate_result.result == CheckResult.PASS:
                completed_event = self._events.emit(
                    run_metrics_path=metrics_path,
                    run_id=ctx.run_id,
                    event_type=EventType.WORKFLOW_TRANSITION_COMPLETED,
                    producer="runtime",
                    workflow_state=ctx.current_state,
                    causation_event_id=last_event_id,
                    payload={
                        "from_state": transition.from_state,
                        "to_state": transition.to_state,
                        "result": gate_result.result.value,
                    },
                )
                last_event_id = completed_event.event_id
                return AdvanceResult(
                    transitioned=True,
                    new_state=transition.to_state,
                    blocked_at=None,
                    gate_result=gate_result,
                )

        if last_gate_result is None:
            raise NoEligibleTransitionsError(
                f"No transition result produced from state '{ctx.current_state}'."
            )
        blocked_event = self._events.emit(
            run_metrics_path=metrics_path,
            run_id=ctx.run_id,
            event_type=EventType.RUN_BLOCKED,
            producer="runtime",
            workflow_state=ctx.current_state,
            causation_event_id=last_event_id,
            payload=_blocked_payload(
                blocked_at_state=ctx.current_state,
                attempted_to_states=attempted_to_states,
                gate_result=last_gate_result,
            ),
        )
        last_event_id = blocked_event.event_id
        return AdvanceResult(
            transitioned=False,
            new_state=None,
            blocked_at=ctx.current_state,
            gate_result=last_gate_result,
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

        # Deterministic fallback: traverse transitions from the declared initial
        # workflow state in definition order and advance only when gate checks pass.
        state = self._workflow.states[0]
        evaluator = DefaultGateEvaluator()
        # Infer project root from canonical path runs/<run_id>/artifacts.
        # artifacts_dir.parent -> run_dir, artifacts_dir.parent.parent -> runs,
        # artifacts_dir.parent.parent.parent -> project_root.
        project_root = artifacts_dir.parent.parent.parent
        _devos_canonical = project_root / ".devOS" / "project_inputs"
        project_inputs_root = _devos_canonical if _devos_canonical.is_dir() else project_root
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
                    project_inputs_root=project_inputs_root,
                    artifacts_dir=artifacts_dir,
                    decision_log_path=decision_log_path,
                    schemas=schemas,
                )
                if gate_result.result == CheckResult.PASS:
                    state = transition.to_state
                    transitioned = True
                    break
            if not transitioned:
                return state

        # If the deterministic hop budget is consumed, return when the current
        # state is terminal in this workflow graph (no outbound transitions).
        # Otherwise, treat as non-terminating traversal/cycle and fail closed.
        if not self.get_eligible_transitions(state):
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


def _blocked_payload(
    blocked_at_state: str,
    attempted_to_states: list[str],
    gate_result: GateResult,
) -> dict:
    failed_checks = [check for check in gate_result.checks if check.result == CheckResult.FAIL]

    missing_artifacts = sorted(
        {
            check.subject
            for check in failed_checks
            if check.check_type in {CheckType.INPUT_PRESENCE, CheckType.ARTIFACT_PRESENCE}
        }
    )
    missing_approvals = sorted(
        {check.subject for check in failed_checks if check.check_type == CheckType.APPROVAL}
    )
    failed_conditions = [_failed_condition_detail(check) for check in failed_checks if check.check_type == CheckType.CONDITION]

    blocking_reason = "gate_check"
    if missing_artifacts:
        blocking_reason = "missing_artifact"
    elif missing_approvals:
        blocking_reason = "missing_approval"
    elif failed_conditions:
        blocking_reason = "failed_condition"

    return {
        "blocked_at_state": blocked_at_state,
        "blocking_reason": blocking_reason,
        "attempted_to_states": attempted_to_states,
        "missing_artifacts": missing_artifacts,
        "missing_approvals": missing_approvals,
        "failed_conditions": failed_conditions,
    }


def _failed_condition_detail(check: GateCheckDetail) -> dict:
    expected = "unknown"
    actual = "missing"
    detail = check.detail or ""
    if ": expected '" in detail and "', got '" in detail and detail.endswith("'."):
        _, rest = detail.split(": expected '", 1)
        expected_part, actual_part = rest.split("', got '", 1)
        expected = expected_part
        actual = actual_part[:-2]
    return {
        "field": check.subject,
        "expected": expected,
        "actual": actual,
    }

