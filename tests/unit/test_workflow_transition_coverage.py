from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.engine.gate_evaluator import GateEvaluator
from kernel.framework.schema_loader import load_schema
from kernel.framework.workflow_loader import load_workflow
from kernel.types.gate import CheckResult


class WorkflowTransitionCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_default_workflow_transition_order_is_deterministic(self) -> None:
        workflow = load_workflow(self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml")
        sequence = [(t.from_state, t.to_state) for t in workflow.transitions]
        self.assertEqual(
            sequence,
            [
                ("INIT", "PLANNING"),
                ("INIT", "FAILED"),
                ("PLANNING", "ARCH_CHECK"),
                ("ARCH_CHECK", "IMPLEMENTING"),
                ("IMPLEMENTING", "TESTING"),
                ("TESTING", "REVIEWING"),
                ("REVIEWING", "ACCEPTED"),
                ("REVIEWING", "ACCEPTED_WITH_DEBT"),
                ("REVIEWING", "FAILED"),
            ],
        )

    def test_improvement_cycle_transition_order_is_deterministic(self) -> None:
        workflow = load_workflow(self.repo_root / "framework" / "workflows" / "improvement_cycle.yaml")
        sequence = [(t.from_state, t.to_state) for t in workflow.transitions]
        self.assertEqual(
            sequence,
            [
                ("OBSERVE", "REFLECT"),
                ("REFLECT", "PROPOSE"),
                ("PROPOSE", "HUMAN_DECISION"),
            ],
        )

    @unittest.skip("release_workflow removed from framework in v1 simplification")
    def test_release_workflow_transition_order_is_deterministic(self) -> None:
        pass

    def test_default_init_to_planning_transition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml")
        transition = next(t for t in workflow.transitions if (t.from_state, t.to_state) == ("INIT", "PLANNING"))
        evaluator = GateEvaluator()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in (
                "domain_scope.md",
                "domain_rules.md",
                "source_policy.md",
                "glossary.md",
                "architecture_contract.md",
            ):
                (root / name).write_text("ok", encoding="utf-8")
            artifacts = root / "runs" / "RUN-20260314-0001" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            result = evaluator.evaluate(
                transition=transition,
                project_inputs_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={},
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_improvement_observe_to_reflect_transition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "framework" / "workflows" / "improvement_cycle.yaml")
        transition = next(t for t in workflow.transitions if (t.from_state, t.to_state) == ("OBSERVE", "REFLECT"))
        evaluator = GateEvaluator()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0002" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "run_metrics.json").write_text('{"events": []}', encoding="utf-8")
            (artifacts / "test_report.json").write_text("{}", encoding="utf-8")
            (artifacts / "review_result.md").write_text(
                "id: RR-I\nsupersedes_id: null\noutcome: ACCEPTED\n\n## Summary\nok\n",
                encoding="utf-8",
            )
            result = evaluator.evaluate(
                transition=transition,
                project_inputs_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={
                    "review_result": load_schema(
                        self.repo_root / "framework" / "artifacts" / "schemas" / "review_result.schema.md"
                    )
                },
            )
            self.assertEqual(result.result, CheckResult.PASS)

    @unittest.skip("release_workflow removed from framework in v1 simplification")
    def test_release_init_to_preparing_transition_is_executable(self) -> None:
        pass

    @unittest.skip("release_workflow removed from framework in v1 simplification")
    def test_release_review_to_failed_reject_condition_is_executable(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
