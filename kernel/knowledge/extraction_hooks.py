from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kernel.events.event_system import EventSystem
from kernel.types.event import EventType
from kernel.types.run import RunContext


@dataclass(frozen=True)
class ExtractionTrigger:
    trigger_point: str
    workflow_location: str
    responsible_roles: tuple[str, ...]
    source_artifacts: tuple[str, ...]


EXTRACTION_TRIGGERS: dict[str, ExtractionTrigger] = {
    "ACCEPTED": ExtractionTrigger(
        trigger_point="delivery_run_accepted",
        workflow_location="default_workflow.yaml ACCEPTED",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "decision_log.yaml", "design_tradeoffs.md"),
    ),
    "ACCEPTED_WITH_DEBT": ExtractionTrigger(
        trigger_point="delivery_run_accepted_with_debt",
        workflow_location="default_workflow.yaml ACCEPTED_WITH_DEBT",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "decision_log.yaml", "design_tradeoffs.md"),
    ),
    "FAILED": ExtractionTrigger(
        trigger_point="delivery_run_failed",
        workflow_location="default_workflow.yaml FAILED",
        responsible_roles=("agent_reflector", "human"),
        source_artifacts=("review_result.md", "arch_review_record.md"),
    ),
    "OBSERVE": ExtractionTrigger(
        trigger_point="improvement_cycle_observe",
        workflow_location="improvement_cycle.yaml OBSERVE",
        responsible_roles=("agent_reflector",),
        source_artifacts=("run_metrics.json", "test_report.json", "review_result.md"),
    ),
}


def check_triggers(terminal_state: str) -> ExtractionTrigger | None:
    return EXTRACTION_TRIGGERS.get(terminal_state)


def log_trigger(
    ctx: RunContext,
    trigger: ExtractionTrigger,
    event_system: EventSystem,
    run_metrics_path: Path,
    causation_event_id: str | None,
) -> None:
    event_system.emit(
        run_metrics_path=run_metrics_path,
        run_id=ctx.run_id,
        event_type=EventType.KNOWLEDGE_EXTRACTION_TRIGGERED,
        producer="runtime",
        workflow_state=ctx.current_state,
        causation_event_id=causation_event_id,
        payload={
            "trigger_point": trigger.trigger_point,
            "workflow_location": trigger.workflow_location,
            "responsible_roles": list(trigger.responsible_roles),
            "source_artifacts": list(trigger.source_artifacts),
            "kind": "knowledge_extraction_trigger",
        },
    )

