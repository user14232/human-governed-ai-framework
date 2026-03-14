from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.decisions.decision_system import (
    DecisionLogParseError,
    DecisionSystem,
    SignalType,
)
from runtime.events.event_system import EventSystem
from runtime.store.run_store import run_metrics_path
from runtime.types.run import RunContext
from runtime.types.workflow import WorkflowDefinition


class DecisionSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WorkflowDefinition(
            workflow_id="wf",
            version="v1",
            states=("HUMAN_DECISION",),
            transitions=(),
            artifacts_used=(),
        )

    def test_process_new_entries_maps_approve_reject_defer_signals(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._make_context(root)
            log_path = ctx.run_dir / "decision_log.yaml"
            log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references:\n"
                "      - artifact: implementation_plan.yaml\n"
                "        artifact_id: IP-1\n"
                "        artifact_hash: h1\n"
                "    rationale: ok\n"
                "    supersedes_decision_id: null\n"
                "  - decision_id: D-2\n"
                "    timestamp: '2026-03-14T11:10:00Z'\n"
                "    human_identity: bob\n"
                "    decision: reject\n"
                "    scope: implementation\n"
                "    references:\n"
                "      - artifact: implementation_plan.yaml\n"
                "        artifact_id: IP-1\n"
                "        artifact_hash: h1\n"
                "    rationale: changes required\n"
                "    supersedes_decision_id: null\n"
                "  - decision_id: D-3\n"
                "    timestamp: '2026-03-14T11:20:00Z'\n"
                "    human_identity: chris\n"
                "    decision: defer\n"
                "    scope: release\n"
                "    references: []\n"
                "    rationale: hold\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )

            system = DecisionSystem(event_system=EventSystem())
            signals = system.process_new_entries(ctx, log_path, last_known_count=0, schemas={})

            self.assertEqual([s.signal_type for s in signals], [SignalType.GATE_RECHECK, SignalType.REWORK, SignalType.DEFERRED])
            self.assertIsNone(signals[0].artifact_ref)
            self.assertIsNotNone(signals[1].artifact_ref)
            self.assertEqual(signals[1].artifact_ref.name, "implementation_plan.yaml")  # type: ignore[union-attr]
            self.assertIsNone(signals[2].artifact_ref)

            metrics = json.loads(run_metrics_path(ctx.run_dir).read_text(encoding="utf-8"))
            event_types = [event["event_type"] for event in metrics["events"]]
            self.assertEqual(
                event_types,
                [
                    "decision.recorded",
                    "decision.recorded",
                    "run.rework_started",
                    "decision.recorded",
                    "run.blocked",
                ],
            )
            # Causation chain is explicit: follow-up events reference their decision.recorded cause.
            self.assertEqual(metrics["events"][2]["causation_event_id"], metrics["events"][1]["event_id"])
            self.assertEqual(metrics["events"][4]["causation_event_id"], metrics["events"][3]["event_id"])
            self.assertEqual(metrics["events"][2]["payload"]["reason"], "reject_decision")
            self.assertEqual(metrics["events"][4]["payload"]["blocking_reason"], "deferred_decision")

    def test_get_new_entries_returns_empty_when_no_new_items(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._make_context(root)
            log_path = ctx.run_dir / "decision_log.yaml"
            log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references: []\n"
                "    rationale: ok\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            system = DecisionSystem()
            self.assertEqual(system.get_new_entries(log_path, last_known_count=1), [])

    def test_malformed_entry_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._make_context(root)
            log_path = ctx.run_dir / "decision_log.yaml"
            log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    scope: implementation\n"
                "    references: []\n"
                "    rationale: ok\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            system = DecisionSystem()
            with self.assertRaises(DecisionLogParseError):
                system.load_all(log_path)

    def test_find_approval_matches_id_hash_and_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._make_context(root)
            log_path = ctx.run_dir / "decision_log.yaml"
            log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references:\n"
                "      - artifact: implementation_plan.yaml\n"
                "        artifact_id: IP-1\n"
                "        artifact_hash: h1\n"
                "    rationale: ok\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            system = DecisionSystem()
            entries = system.load_all(log_path)

            match = system.find_approval(
                entries=entries,
                artifact_id="IP-1",
                artifact_hash="h1",
                artifact_created_at="2026-03-14T10:00:00Z",
            )
            self.assertIsNotNone(match)
            self.assertEqual(match.decision_id, "D-1")  # type: ignore[union-attr]

            no_match_hash = system.find_approval(
                entries=entries,
                artifact_id="IP-1",
                artifact_hash="other",
                artifact_created_at="2026-03-14T10:00:00Z",
            )
            self.assertIsNone(no_match_hash)

            no_match_timestamp = system.find_approval(
                entries=entries,
                artifact_id="IP-1",
                artifact_hash="h1",
                artifact_created_at="2026-03-14T12:00:00Z",
            )
            self.assertIsNone(no_match_timestamp)

    def _make_context(self, root: Path) -> RunContext:
        run_dir = root / "runs" / "RUN-20260314-0001"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        return RunContext(
            run_id="RUN-20260314-0001",
            project_root=root,
            run_dir=run_dir,
            artifacts_dir=artifacts_dir,
            workflow_def=self.workflow,
            current_state="HUMAN_DECISION",
        )


if __name__ == "__main__":
    unittest.main()

