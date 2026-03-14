from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.engine.gate_evaluator import GateEvaluator
from runtime.framework.schema_loader import load_schema
from runtime.framework.workflow_loader import load_workflow
from runtime.types.gate import CheckResult


class WorkflowTransitionCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_default_workflow_transition_order_is_deterministic(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "default_workflow.yaml")
        sequence = [(t.from_state, t.to_state) for t in workflow.transitions]
        self.assertEqual(
            sequence,
            [
                ("INIT", "PLANNING"),
                ("INIT", "FAILED"),
                ("PLANNING", "ARCH_CHECK"),
                ("ARCH_CHECK", "TEST_DESIGN"),
                ("TEST_DESIGN", "BRANCH_READY"),
                ("BRANCH_READY", "IMPLEMENTING"),
                ("IMPLEMENTING", "TESTING"),
                ("TESTING", "REVIEWING"),
                ("REVIEWING", "ACCEPTED"),
                ("REVIEWING", "ACCEPTED_WITH_DEBT"),
                ("REVIEWING", "FAILED"),
            ],
        )

    def test_improvement_cycle_transition_order_is_deterministic(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "improvement_cycle.yaml")
        sequence = [(t.from_state, t.to_state) for t in workflow.transitions]
        self.assertEqual(
            sequence,
            [
                ("OBSERVE", "REFLECT"),
                ("REFLECT", "PROPOSE"),
                ("PROPOSE", "HUMAN_DECISION"),
            ],
        )

    def test_release_workflow_transition_order_is_deterministic(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "release_workflow.yaml")
        sequence = [(t.from_state, t.to_state) for t in workflow.transitions]
        self.assertEqual(
            sequence,
            [
                ("RELEASE_INIT", "RELEASE_PREPARING"),
                ("RELEASE_INIT", "RELEASE_FAILED"),
                ("RELEASE_PREPARING", "RELEASE_REVIEW"),
                ("RELEASE_REVIEW", "RELEASED"),
                ("RELEASE_REVIEW", "RELEASE_FAILED"),
            ],
        )

    def test_default_init_to_planning_transition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "default_workflow.yaml")
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
                project_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={},
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_improvement_observe_to_reflect_transition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "improvement_cycle.yaml")
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
                project_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={
                    "review_result": load_schema(
                        self.repo_root / "artifacts" / "schemas" / "review_result.schema.md"
                    )
                },
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_release_init_to_preparing_transition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "release_workflow.yaml")
        transition = next(
            t for t in workflow.transitions if (t.from_state, t.to_state) == ("RELEASE_INIT", "RELEASE_PREPARING")
        )
        evaluator = GateEvaluator()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0003" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "review_result.md").write_text(
                "id: RR-R\nsupersedes_id: null\noutcome: ACCEPTED\n\n## Summary\nok\n",
                encoding="utf-8",
            )
            (artifacts / "test_report.json").write_text("{}", encoding="utf-8")
            (artifacts / "decision_log.yaml").write_text(
                "schema_version: v1\ndecisions: []\n", encoding="utf-8"
            )
            result = evaluator.evaluate(
                transition=transition,
                project_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas={
                    "review_result": load_schema(
                        self.repo_root / "artifacts" / "schemas" / "review_result.schema.md"
                    )
                },
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_release_review_to_failed_reject_condition_is_executable(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "release_workflow.yaml")
        transition = next(
            t for t in workflow.transitions if (t.from_state, t.to_state) == ("RELEASE_REVIEW", "RELEASE_FAILED")
        )
        evaluator = GateEvaluator()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0004" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "decision_log.yaml").write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-R\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: bob\n"
                "    decision: reject\n"
                "    scope: release\n"
                "    references:\n"
                "      - artifact: release_metadata.json\n"
                "        artifact_id: RM-R\n"
                "        artifact_hash: deadbeef\n"
                "    rationale: blocked\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            (artifacts / "release_metadata.json").write_text(
                "{\n"
                '  "id": "RM-R",\n'
                '  "supersedes_id": null,\n'
                '  "created_at": "2026-03-14T10:00:00Z",\n'
                '  "run_id": "RUN-20260314-0004",\n'
                '  "inputs": {\n'
                '    "review_result_ref": "RR-R",\n'
                '    "review_result_hash": null,\n'
                '    "test_report_run_id": "RUN-20260314-0004",\n'
                '    "implementation_plan_id": "IP-R"\n'
                "  },\n"
                '  "artifacts": [{"name": "review_result.md", "ref": "RR-R", "hash": null}],\n'
                '  "environment": {"os": "win32", "tool_versions": {"python": "3.14"}}\n'
                "}\n",
                encoding="utf-8",
            )
            result = evaluator.evaluate(
                transition=transition,
                project_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts / "decision_log.yaml",
                schemas={
                    "release_metadata": load_schema(
                        self.repo_root / "artifacts" / "schemas" / "release_metadata.schema.json"
                    )
                },
            )
            self.assertEqual(result.result, CheckResult.PASS)


if __name__ == "__main__":
    unittest.main()
