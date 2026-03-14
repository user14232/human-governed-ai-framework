from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from runtime.framework.schema_loader import load_schema
from runtime.engine.workflow_engine import (
    NoEligibleTransitionsError,
    WorkflowEngine,
)
from runtime.store.run_store import run_metrics_path
from runtime.types.artifact import ArtifactSchema
from runtime.types.gate import CheckResult, GateResult
from runtime.types.run import RunContext
from runtime.types.workflow import RequiresBlock, Transition, WorkflowDefinition


@dataclass
class FakeEvaluator:
    results: dict[str, CheckResult]
    calls: list[str]

    def evaluate(  # type: ignore[override]
        self,
        transition: Transition,
        project_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        _ = (project_root, artifacts_dir, decision_log_path, schemas)
        self.calls.append(f"{transition.from_state}->{transition.to_state}")
        result = self.results.get(f"{transition.from_state}->{transition.to_state}", CheckResult.FAIL)
        return GateResult(transition=transition, result=result, checks=())


class WorkflowEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def _workflow(self) -> WorkflowDefinition:
        return WorkflowDefinition(
            workflow_id="wf",
            version="v1",
            states=("INIT", "A", "B"),
            transitions=(
                Transition(
                    from_state="INIT",
                    to_state="A",
                    requires=RequiresBlock(
                        inputs_present=True,
                        artifacts=(),
                        human_approval=(),
                        conditions={},
                    ),
                    notes=None,
                ),
                Transition(
                    from_state="INIT",
                    to_state="B",
                    requires=RequiresBlock(
                        inputs_present=True,
                        artifacts=(),
                        human_approval=(),
                        conditions={},
                    ),
                    notes=None,
                ),
            ),
            artifacts_used=(),
        )

    def _ctx(self, root: Path) -> RunContext:
        run_dir = root / "runs" / "RUN-20260314-0001"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        return RunContext(
            run_id="RUN-20260314-0001",
            project_root=root,
            run_dir=run_dir,
            artifacts_dir=artifacts,
            workflow_def=self._workflow(),
            current_state="INIT",
        )

    def test_get_eligible_transitions_preserves_definition_order(self) -> None:
        engine = WorkflowEngine(self._workflow())
        eligible = engine.get_eligible_transitions("INIT")
        self.assertEqual([f"{t.from_state}->{t.to_state}" for t in eligible], ["INIT->A", "INIT->B"])

    def test_advance_executes_at_most_one_transition(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._ctx(root)
            engine = WorkflowEngine(ctx.workflow_def)
            evaluator = FakeEvaluator(results={"INIT->A": CheckResult.PASS}, calls=[])
            result = engine.advance(
                ctx=ctx,
                evaluator=evaluator,
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas={},
            )
            self.assertTrue(result.transitioned)
            self.assertEqual(result.new_state, "A")
            self.assertEqual(evaluator.calls, ["INIT->A"])
            payload = json.loads(run_metrics_path(ctx.run_dir).read_text(encoding="utf-8"))
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertEqual(
                event_types,
                ["workflow.transition_checked", "workflow.transition_completed"],
            )

    def test_advance_reports_blocked_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._ctx(root)
            engine = WorkflowEngine(ctx.workflow_def)
            evaluator = FakeEvaluator(results={"INIT->A": CheckResult.FAIL, "INIT->B": CheckResult.FAIL}, calls=[])
            result = engine.advance(
                ctx=ctx,
                evaluator=evaluator,
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas={},
            )
            self.assertFalse(result.transitioned)
            self.assertEqual(result.blocked_at, "INIT")
            self.assertEqual(evaluator.calls, ["INIT->A", "INIT->B"])
            payload = json.loads(run_metrics_path(ctx.run_dir).read_text(encoding="utf-8"))
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertEqual(
                event_types,
                ["workflow.transition_checked", "workflow.transition_checked", "run.blocked"],
            )
            blocked_payload = payload["events"][-1]["payload"]
            self.assertEqual(blocked_payload["blocked_at_state"], "INIT")
            self.assertEqual(blocked_payload["blocking_reason"], "gate_check")
            self.assertEqual(blocked_payload["attempted_to_states"], ["A", "B"])

    def test_advance_uses_later_candidate_when_first_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._ctx(root)
            engine = WorkflowEngine(ctx.workflow_def)
            evaluator = FakeEvaluator(results={"INIT->A": CheckResult.FAIL, "INIT->B": CheckResult.PASS}, calls=[])
            result = engine.advance(
                ctx=ctx,
                evaluator=evaluator,
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas={},
            )
            self.assertTrue(result.transitioned)
            self.assertEqual(result.new_state, "B")
            self.assertEqual(evaluator.calls, ["INIT->A", "INIT->B"])
            payload = json.loads(run_metrics_path(ctx.run_dir).read_text(encoding="utf-8"))
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertEqual(
                event_types,
                [
                    "workflow.transition_checked",
                    "workflow.transition_checked",
                    "workflow.transition_completed",
                ],
            )

    def test_advance_raises_when_no_eligible_transition(self) -> None:
        workflow = WorkflowDefinition(
            workflow_id="wf",
            version="v1",
            states=("INIT",),
            transitions=(),
            artifacts_used=(),
        )
        engine = WorkflowEngine(workflow)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = RunContext(
                run_id="RUN-20260314-0001",
                project_root=root,
                run_dir=root / "runs" / "RUN-20260314-0001",
                artifacts_dir=root / "runs" / "RUN-20260314-0001" / "artifacts",
                workflow_def=workflow,
                current_state="INIT",
            )
            evaluator = FakeEvaluator(results={}, calls=[])
            with self.assertRaises(NoEligibleTransitionsError):
                engine.advance(ctx, evaluator, ctx.run_dir / "decision_log.yaml", {})

    def test_reconstruct_state_from_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_metrics = root / "run_metrics.json"
            run_metrics.write_text(
                json.dumps(
                    {
                        "events": [
                            {"event_type": "workflow.transition_completed", "payload": {"to_state": "A"}},
                            {"event_type": "workflow.transition_completed", "payload": {"to_state": "B"}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            engine = WorkflowEngine(self._workflow())
            state = engine.reconstruct_state(
                artifacts_dir=root / "artifacts",
                decision_log_path=root / "decision_log.yaml",
                schemas={},
                run_metrics_path=run_metrics,
            )
            self.assertEqual(state, "B")

    def test_reconstruct_state_fallback_without_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            engine = WorkflowEngine(self._workflow())
            state = engine.reconstruct_state(
                artifacts_dir=root / "artifacts",
                decision_log_path=root / "decision_log.yaml",
                schemas={},
                run_metrics_path=None,
            )
            self.assertEqual(state, "INIT")

    def test_reconstruct_state_fallback_uses_declared_initial_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workflow = WorkflowDefinition(
                workflow_id="wf-release",
                version="v1",
                states=("RELEASE_INIT", "RELEASE_PREPARING"),
                transitions=(),
                artifacts_used=(),
            )
            engine = WorkflowEngine(workflow)
            state = engine.reconstruct_state(
                artifacts_dir=root / "artifacts",
                decision_log_path=root / "decision_log.yaml",
                schemas={},
                run_metrics_path=None,
            )
            self.assertEqual(state, "RELEASE_INIT")

    def test_reconstruct_state_fallback_traverses_on_gate_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0001" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            for name in (
                "domain_scope.md",
                "domain_rules.md",
                "source_policy.md",
                "glossary.md",
                "architecture_contract.md",
            ):
                (root / name).write_text("ok", encoding="utf-8")
            engine = WorkflowEngine(self._workflow())
            state = engine.reconstruct_state(
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={},
                run_metrics_path=None,
            )
            self.assertEqual(state, "A")

    def test_reconstruct_state_fallback_checks_all_candidates_before_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0001" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            workflow = WorkflowDefinition(
                workflow_id="wf-branch",
                version="v1",
                states=("INIT", "A", "B"),
                transitions=(
                    Transition(
                        from_state="INIT",
                        to_state="A",
                        requires=RequiresBlock(
                            inputs_present=True,
                            artifacts=(),
                            human_approval=(),
                            conditions={},
                        ),
                        notes=None,
                    ),
                    Transition(
                        from_state="INIT",
                        to_state="B",
                        requires=RequiresBlock(
                            inputs_present=False,
                            artifacts=(),
                            human_approval=(),
                            conditions={},
                        ),
                        notes=None,
                    ),
                ),
                artifacts_used=(),
            )
            engine = WorkflowEngine(workflow)
            state = engine.reconstruct_state(
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={},
                run_metrics_path=None,
            )
            self.assertEqual(state, "B")

    def test_reconstruct_state_fallback_returns_terminal_at_hop_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0001" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            workflow = WorkflowDefinition(
                workflow_id="wf-improvement",
                version="v1",
                states=("OBSERVE", "REFLECT", "PROPOSE", "HUMAN_DECISION"),
                transitions=(
                    Transition(
                        from_state="OBSERVE",
                        to_state="REFLECT",
                        requires=RequiresBlock(
                            inputs_present=None,
                            artifacts=("run_metrics.json", "test_report.json", "review_result.md"),
                            human_approval=(),
                            conditions={},
                        ),
                        notes=None,
                    ),
                    Transition(
                        from_state="REFLECT",
                        to_state="PROPOSE",
                        requires=RequiresBlock(
                            inputs_present=None,
                            artifacts=("reflection_notes.md",),
                            human_approval=(),
                            conditions={},
                        ),
                        notes=None,
                    ),
                    Transition(
                        from_state="PROPOSE",
                        to_state="HUMAN_DECISION",
                        requires=RequiresBlock(
                            inputs_present=None,
                            artifacts=("improvement_proposal.md", "decision_log.yaml"),
                            human_approval=("improvement_proposal.md",),
                            conditions={},
                        ),
                        notes=None,
                    ),
                ),
                artifacts_used=(),
            )
            for name, content in (
                ("run_metrics.json", '{"events": []}'),
                ("test_report.json", "{}"),
                ("review_result.md", "id: RR-1\nsupersedes_id: null\noutcome: ACCEPTED\n\n## Summary\nok\n"),
                (
                    "reflection_notes.md",
                    "id: RN-1\nsupersedes_id: null\n\n## Evidence referenced\n- ok\n## Observations (facts)\n- ok\n## Hypotheses (explicitly labeled)\n- ok\n## Open questions\n- ok\n",
                ),
                (
                    "improvement_proposal.md",
                    "id: IP-1\nsupersedes_id: null\n\n## 1) Problem statement (evidence-cited)\n- ok\n## 2) Proposed change\n- ok\n## 3) Expected impact\n- ok\n## 4) Risks and mitigations\n- ok\n## 5) Required human decisions\n- ok\n## 6) Decision reference\n- decision_id: D-1\n",
                ),
                (
                    "decision_log.yaml",
                    "schema_version: v1\ndecisions:\n  - decision_id: D-1\n    timestamp: '2026-03-14T20:55:00Z'\n    human_identity: alice\n    decision: approve\n    scope: improvement_cycle\n    references:\n      - artifact: improvement_proposal.md\n        artifact_id: IP-1\n        artifact_hash: ''\n    rationale: ok\n    supersedes_decision_id: null\n",
                ),
            ):
                (artifacts / name).write_text(content, encoding="utf-8")

            schemas = {
                "improvement_proposal": load_schema(
                    self.repo_root / "artifacts" / "schemas" / "improvement_proposal.schema.md"
                )
            }

            engine = WorkflowEngine(workflow)
            state = engine.reconstruct_state(
                artifacts_dir=artifacts,
                decision_log_path=artifacts / "decision_log.yaml",
                schemas=schemas,
                run_metrics_path=None,
            )
            self.assertEqual(state, "HUMAN_DECISION")


if __name__ == "__main__":
    unittest.main()

