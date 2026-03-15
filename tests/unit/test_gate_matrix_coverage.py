from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.engine.gate_evaluator import GateEvaluator
from runtime.framework.schema_loader import load_schema
from runtime.types.gate import CheckResult
from runtime.types.workflow import RequiresBlock, Transition


class GateMatrixCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.evaluator = GateEvaluator()
        self.schemas = {
            "implementation_plan": load_schema(
                self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
            ),
            "arch_review_record": load_schema(
                self.repo_root / "framework" / "artifacts" / "schemas" / "arch_review_record.schema.md"
            ),
            "review_result": load_schema(
                self.repo_root / "framework" / "artifacts" / "schemas" / "review_result.schema.md"
            ),
        }

    def test_tc01_init_to_planning_inputs_missing_fails(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            transition = Transition(
                from_state="INIT",
                to_state="PLANNING",
                requires=RequiresBlock(
                    inputs_present=True,
                    artifacts=(),
                    human_approval=(),
                    conditions={},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.FAIL)

    def test_tc02_init_to_planning_inputs_present_passes(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_required_inputs(project_root)
            transition = Transition(
                from_state="INIT",
                to_state="PLANNING",
                requires=RequiresBlock(
                    inputs_present=True,
                    artifacts=(),
                    human_approval=(),
                    conditions={},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_tc03_planning_to_arch_check_plan_not_approved_fails(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_implementation_plan(artifacts_dir, artifact_id="IP-3")
            transition = Transition(
                from_state="PLANNING",
                to_state="ARCH_CHECK",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("implementation_plan.yaml",),
                    human_approval=("implementation_plan.yaml",),
                    conditions={},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.FAIL)

    def test_tc04_planning_to_arch_check_plan_approved_matching_hash_passes(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            plan_path = self._write_implementation_plan(artifacts_dir, artifact_id="IP-4")
            plan_hash = self.evaluator._artifacts.compute_hash(plan_path)  # noqa: SLF001
            decision_log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-4\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references:\n"
                "      - artifact: implementation_plan.yaml\n"
                "        artifact_id: IP-4\n"
                f"        artifact_hash: {plan_hash}\n"
                "    rationale: approved\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            transition = Transition(
                from_state="PLANNING",
                to_state="ARCH_CHECK",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("implementation_plan.yaml",),
                    human_approval=("implementation_plan.yaml",),
                    conditions={},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_tc05_arch_check_to_test_design_change_required_fails(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_arch_review_record(artifacts_dir, artifact_id="AR-5", outcome="CHANGE_REQUIRED")
            transition = Transition(
                from_state="ARCH_CHECK",
                to_state="TEST_DESIGN",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("arch_review_record.md",),
                    human_approval=(),
                    conditions={"arch_review_outcome": "PASS"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.FAIL)

    def test_tc06_arch_check_to_test_design_pass_outcome_passes(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_arch_review_record(artifacts_dir, artifact_id="AR-6", outcome="PASS")
            transition = Transition(
                from_state="ARCH_CHECK",
                to_state="TEST_DESIGN",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("arch_review_record.md",),
                    human_approval=(),
                    conditions={"arch_review_outcome": "PASS"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_tc07_reviewing_to_accepted_failed_outcome_fails(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_review_result(artifacts_dir, artifact_id="RR-7", outcome="FAILED")
            transition = Transition(
                from_state="REVIEWING",
                to_state="ACCEPTED",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("review_result.md",),
                    human_approval=(),
                    conditions={"review_outcome": "ACCEPTED"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.FAIL)

    def test_tc08_reviewing_to_accepted_accepted_outcome_passes(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_review_result(artifacts_dir, artifact_id="RR-8", outcome="ACCEPTED")
            transition = Transition(
                from_state="REVIEWING",
                to_state="ACCEPTED",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("review_result.md",),
                    human_approval=(),
                    conditions={"review_outcome": "ACCEPTED"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def test_tc09_reviewing_to_accepted_with_debt_without_approval_fails(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            self._write_review_result(artifacts_dir, artifact_id="RR-9", outcome="ACCEPTED_WITH_DEBT")
            transition = Transition(
                from_state="REVIEWING",
                to_state="ACCEPTED_WITH_DEBT",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("review_result.md",),
                    human_approval=("review_result.md",),
                    conditions={"review_outcome": "ACCEPTED_WITH_DEBT"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.FAIL)

    def test_tc10_reviewing_to_accepted_with_debt_with_approval_passes(self) -> None:
        with self._fixture() as (project_root, artifacts_dir, decision_log_path):
            review_path = self._write_review_result(
                artifacts_dir, artifact_id="RR-10", outcome="ACCEPTED_WITH_DEBT"
            )
            review_hash = self.evaluator._artifacts.compute_hash(review_path)  # noqa: SLF001
            decision_log_path.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-10\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: review\n"
                "    references:\n"
                "      - artifact: review_result.md\n"
                "        artifact_id: RR-10\n"
                f"        artifact_hash: {review_hash}\n"
                "    rationale: debt accepted\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            transition = Transition(
                from_state="REVIEWING",
                to_state="ACCEPTED_WITH_DEBT",
                requires=RequiresBlock(
                    inputs_present=None,
                    artifacts=("review_result.md",),
                    human_approval=("review_result.md",),
                    conditions={"review_outcome": "ACCEPTED_WITH_DEBT"},
                ),
                notes=None,
            )
            result = self.evaluator.evaluate(
                transition=transition,
                project_inputs_root=project_root,
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                schemas=self.schemas,
            )
            self.assertEqual(result.result, CheckResult.PASS)

    def _fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        run_dir = root / "runs" / "RUN-20260314-0001"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        decision_log_path = run_dir / "decision_log.yaml"
        return _FixtureContext(td, root, artifacts_dir, decision_log_path)

    @staticmethod
    def _write_required_inputs(project_root: Path) -> None:
        for name in (
            "domain_scope.md",
            "domain_rules.md",
            "source_policy.md",
            "glossary.md",
            "architecture_contract.md",
        ):
            (project_root / name).write_text("ok", encoding="utf-8")

    @staticmethod
    def _write_implementation_plan(artifacts_dir: Path, artifact_id: str) -> Path:
        path = artifacts_dir / "implementation_plan.yaml"
        path.write_text(
            f"id: {artifact_id}\n"
            "supersedes_id: null\n"
            "created_at: '2026-03-14T10:00:00Z'\n"
            "inputs:\n"
            "  change_intent_id: CI-1\n"
            "  architecture_contract_ref: architecture_contract.md\n"
            "plan_items:\n"
            "  - id: P1\n"
            "    title: t\n"
            "    description: d\n"
            "    dependencies: []\n"
            "    outputs: []\n"
            "    constraints: []\n"
            "non_goals: []\n"
            "risks: []\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_arch_review_record(artifacts_dir: Path, artifact_id: str, outcome: str) -> Path:
        path = artifacts_dir / "arch_review_record.md"
        path.write_text(
            f"id: {artifact_id}\n"
            "supersedes_id: null\n"
            f"outcome: {outcome}\n\n"
            "## Summary\n"
            "ok\n\n"
            "## Outcome\n"
            "ok\n\n"
            "## Findings\n"
            "ok\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_review_result(artifacts_dir: Path, artifact_id: str, outcome: str) -> Path:
        path = artifacts_dir / "review_result.md"
        path.write_text(
            f"id: {artifact_id}\n"
            "supersedes_id: null\n"
            f"outcome: {outcome}\n\n"
            "## Summary\n"
            "ok\n\n"
            "## Outcome\n"
            "ok\n\n"
            "## Evidence\n"
            "ok\n\n"
            "## Findings\n"
            "ok\n",
            encoding="utf-8",
        )
        return path


class _FixtureContext:
    def __init__(
        self,
        td: tempfile.TemporaryDirectory[str],
        project_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
    ) -> None:
        self._td = td
        self.project_root = project_root
        self.artifacts_dir = artifacts_dir
        self.decision_log_path = decision_log_path

    def __enter__(self) -> tuple[Path, Path, Path]:
        return self.project_root, self.artifacts_dir, self.decision_log_path

    def __exit__(self, exc_type, exc, tb) -> None:
        self._td.cleanup()


if __name__ == "__main__":
    unittest.main()
