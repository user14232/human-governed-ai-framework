from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kernel.types.run import RunId


class EventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_BLOCKED = "run.blocked"
    RUN_RESUMED = "run.resumed"
    RUN_REWORK_STARTED = "run.rework_started"
    WORKFLOW_TRANSITION_CHECKED = "workflow.transition_checked"
    WORKFLOW_TRANSITION_COMPLETED = "workflow.transition_completed"
    AGENT_INVOCATION_STARTED = "agent.invocation_started"
    AGENT_INVOCATION_COMPLETED = "agent.invocation_completed"
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_SUPERSEDED = "artifact.superseded"
    ARTIFACT_VALIDATED = "artifact.validated"
    ARTIFACT_VALIDATION_FAILED = "artifact.validation_failed"
    DECISION_RECORDED = "decision.recorded"
    KNOWLEDGE_EXTRACTION_TRIGGERED = "knowledge.extraction_triggered"


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: EventType
    run_id: RunId
    timestamp: str
    producer: str
    workflow_state: str
    causation_event_id: str | None
    correlation_id: str
    payload: dict

