from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from runtime.engine.workflow_engine import (
    NoEligibleTransitionsError,
    WorkflowEngine,
)
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

    def test_advance_reports_blocked_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ctx = self._ctx(root)
            engine = WorkflowEngine(ctx.workflow_def)
            evaluator = FakeEvaluator(results={"INIT->A": CheckResult.FAIL}, calls=[])
            result = engine.advance(
                ctx=ctx,
                evaluator=evaluator,
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas={},
            )
            self.assertFalse(result.transitioned)
            self.assertEqual(result.blocked_at, "INIT")
            self.assertEqual(evaluator.calls, ["INIT->A"])

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


if __name__ == "__main__":
    unittest.main()

