from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from runtime.events import metrics_writer
from runtime.types.event import EventEnvelope, EventType
from runtime.types.run import RunId


class MalformedEventError(ValueError):
    """Raised when an event envelope misses required fields."""


class EventSystem:
    def emit(
        self,
        run_metrics_path: Path,
        run_id: RunId,
        event_type: EventType,
        producer: str,
        workflow_state: str,
        causation_event_id: str | None,
        payload: dict,
    ) -> EventEnvelope:
        counter = self._next_counter(run_metrics_path)
        event_id = _build_event_id(run_id, counter)
        envelope = EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            producer=producer,
            workflow_state=workflow_state,
            causation_event_id=causation_event_id,
            correlation_id=run_id,
            payload=payload,
        )
        self._validate_envelope(envelope)
        section = (
            "invocation_records"
            if event_type in {EventType.AGENT_INVOCATION_STARTED, EventType.AGENT_INVOCATION_COMPLETED}
            else "events"
        )
        payload_dict = asdict(envelope)
        payload_dict["event_type"] = envelope.event_type.value
        metrics_writer.append_event(run_metrics_path, payload_dict, section)
        return envelope

    def last_event_id(self, run_metrics_path: Path) -> str | None:
        if not run_metrics_path.is_file():
            return None
        import json

        data = json.loads(run_metrics_path.read_text(encoding="utf-8"))
        events = data.get("events", [])
        if not isinstance(events, list) or not events:
            return None
        last = events[-1]
        if not isinstance(last, dict):
            return None
        value = last.get("event_id")
        return str(value) if value else None

    def read_events(
        self,
        run_metrics_path: Path,
        event_type: EventType | None = None,
    ) -> list[EventEnvelope]:
        if not run_metrics_path.is_file():
            return []
        import json

        data = json.loads(run_metrics_path.read_text(encoding="utf-8"))
        events = data.get("events", [])
        if not isinstance(events, list):
            return []
        result: list[EventEnvelope] = []
        for raw in events:
            if not isinstance(raw, dict):
                continue
            raw_type = raw.get("event_type")
            if not isinstance(raw_type, str):
                continue
            try:
                et = EventType(raw_type)
            except ValueError:
                continue
            if event_type and et != event_type:
                continue
            result.append(
                EventEnvelope(
                    event_id=str(raw.get("event_id", "")),
                    event_type=et,
                    run_id=str(raw.get("run_id", "")),
                    timestamp=str(raw.get("timestamp", "")),
                    producer=str(raw.get("producer", "")),
                    workflow_state=str(raw.get("workflow_state", "")),
                    causation_event_id=raw.get("causation_event_id")
                    if raw.get("causation_event_id") is None
                    else str(raw.get("causation_event_id")),
                    correlation_id=str(raw.get("correlation_id", "")),
                    payload=raw.get("payload", {}) if isinstance(raw.get("payload", {}), dict) else {},
                )
            )
        return result

    def _next_counter(self, run_metrics_path: Path) -> int:
        last = self.last_event_id(run_metrics_path)
        if not last:
            return 1
        tail = last.split("-")[-1]
        if not tail.isdigit():
            return 1
        return int(tail) + 1

    @staticmethod
    def _validate_envelope(envelope: EventEnvelope) -> None:
        if not envelope.event_id:
            raise MalformedEventError("event_id is required.")
        if not envelope.run_id:
            raise MalformedEventError("run_id is required.")
        if not envelope.timestamp:
            raise MalformedEventError("timestamp is required.")
        if not envelope.producer:
            raise MalformedEventError("producer is required.")
        if not envelope.workflow_state:
            raise MalformedEventError("workflow_state is required.")
        if not envelope.correlation_id:
            raise MalformedEventError("correlation_id is required.")
        if not isinstance(envelope.payload, dict):
            raise MalformedEventError("payload must be a dict.")


def _build_event_id(run_id: str, counter: int) -> str:
    run_short = run_id.replace("-", "")
    return f"EVT-{run_short}-{counter:04d}"

