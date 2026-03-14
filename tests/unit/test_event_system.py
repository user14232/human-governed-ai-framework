from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.events.event_system import EventSystem
from runtime.events.event_system import MalformedEventError
from runtime.events.metrics_writer import (
    AppendOnlyViolationError,
    EventCounterViolationError,
    append_event,
    file_hash,
    verify_append_only,
)
from runtime.knowledge.extraction_hooks import check_triggers, log_trigger
from runtime.types.event import EventType
from runtime.types.run import RunContext
from runtime.types.workflow import WorkflowDefinition


class EventSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.events = EventSystem()
        self.workflow = WorkflowDefinition(
            workflow_id="wf",
            version="v1",
            states=("INIT", "ACCEPTED"),
            transitions=(),
            artifacts_used=(),
        )

    def test_emit_assigns_monotonic_ids_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            metrics = Path(td) / "run_metrics.json"
            e1 = self.events.emit(
                run_metrics_path=metrics,
                run_id="RUN-20260314-0001",
                event_type=EventType.RUN_STARTED,
                producer="runtime",
                workflow_state="INIT",
                causation_event_id=None,
                payload={"x": 1},
            )
            e2 = self.events.emit(
                run_metrics_path=metrics,
                run_id="RUN-20260314-0001",
                event_type=EventType.WORKFLOW_TRANSITION_COMPLETED,
                producer="runtime",
                workflow_state="PLANNING",
                causation_event_id=e1.event_id,
                payload={"from_state": "INIT", "to_state": "PLANNING"},
            )
            self.assertTrue(e1.event_id.endswith("-0001"))
            self.assertTrue(e2.event_id.endswith("-0002"))
            self.assertEqual(self.events.last_event_id(metrics), e2.event_id)
            self.assertEqual(len(self.events.read_events(metrics)), 2)

    def test_metrics_writer_rejects_non_monotonic_counter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            metrics = Path(td) / "run_metrics.json"
            append_event(metrics, {"event_id": "EVT-ABC-0002"}, "events")
            with self.assertRaises(EventCounterViolationError):
                append_event(metrics, {"event_id": "EVT-ABC-0001"}, "events")

    def test_extraction_trigger_logging_hook(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "runs" / "RUN-20260314-0001"
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            ctx = RunContext(
                run_id="RUN-20260314-0001",
                project_root=root,
                run_dir=run_dir,
                artifacts_dir=artifacts_dir,
                workflow_def=self.workflow,
                current_state="ACCEPTED",
            )
            trigger = check_triggers("ACCEPTED")
            self.assertIsNotNone(trigger)
            metrics = artifacts_dir / "run_metrics.json"
            log_trigger(
                ctx=ctx,
                trigger=trigger,  # type: ignore[arg-type]
                event_system=self.events,
                run_metrics_path=metrics,
                causation_event_id=None,
            )
            payload = json.loads(metrics.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["events"]), 1)
            self.assertEqual(payload["events"][0]["payload"]["kind"], "knowledge_extraction_trigger")
            self.assertTrue(file_hash(metrics))

    def test_verify_append_only_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            metrics = Path(td) / "run_metrics.json"
            append_event(metrics, {"event_id": "EVT-ABC-0001", "payload": {}}, "events")
            prior_hash = file_hash(metrics)

            # Non-append mutation (rewrite beginning) must violate.
            metrics.write_text('{"run_metadata": {}, "events": [], "invocation_records": []}', encoding="utf-8")
            with self.assertRaises(AppendOnlyViolationError):
                verify_append_only(metrics, prior_hash)

    def test_emit_rejects_malformed_envelope_and_does_not_persist(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            metrics = Path(td) / "run_metrics.json"
            with self.assertRaises(MalformedEventError):
                self.events.emit(
                    run_metrics_path=metrics,
                    run_id="RUN-20260314-0001",
                    event_type=EventType.RUN_STARTED,
                    producer="",
                    workflow_state="INIT",
                    causation_event_id=None,
                    payload={"x": 1},
                )
            self.assertFalse(metrics.exists())

    def test_causation_chain_is_navigable_from_latest_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            metrics = Path(td) / "run_metrics.json"
            first = self.events.emit(
                run_metrics_path=metrics,
                run_id="RUN-20260314-0001",
                event_type=EventType.RUN_STARTED,
                producer="runtime",
                workflow_state="INIT",
                causation_event_id=None,
                payload={"step": "start"},
            )
            second = self.events.emit(
                run_metrics_path=metrics,
                run_id="RUN-20260314-0001",
                event_type=EventType.WORKFLOW_TRANSITION_COMPLETED,
                producer="runtime",
                workflow_state="PLANNING",
                causation_event_id=first.event_id,
                payload={"step": "planning"},
            )
            third = self.events.emit(
                run_metrics_path=metrics,
                run_id="RUN-20260314-0001",
                event_type=EventType.WORKFLOW_TRANSITION_COMPLETED,
                producer="runtime",
                workflow_state="ARCH_CHECK",
                causation_event_id=second.event_id,
                payload={"step": "arch_check"},
            )

            events = self.events.read_events(metrics)
            by_id = {event.event_id: event for event in events}
            chain: list[str] = []
            current = by_id[third.event_id]
            while current.causation_event_id is not None:
                chain.append(current.event_id)
                current = by_id[current.causation_event_id]
            chain.append(current.event_id)
            self.assertEqual(chain, [third.event_id, second.event_id, first.event_id])


if __name__ == "__main__":
    unittest.main()

