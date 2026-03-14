from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.engine.gate_evaluator import GateEvaluator
from runtime.framework.schema_loader import load_schema
from runtime.types.gate import CheckResult, CheckType
from runtime.types.workflow import RequiresBlock, Transition


class GateEvaluatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.evaluator = GateEvaluator()

    def test_check_sequence_order_is_fixed(self) -> None:
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
            artifact_name = "implementation_plan.yaml"
            artifact_path = artifacts / artifact_name
            artifact_path.write_text(
                "id: IP-1\n"
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
            artifact_hash = self.evaluator._artifacts.compute_hash(artifact_path)  # noqa: SLF001

            (artifacts.parent / "decision_log.yaml").write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references:\n"
                f"      - artifact: {artifact_name}\n"
                "        artifact_id: IP-1\n"
                f"        artifact_hash: {artifact_hash}\n"
                "    rationale: approved\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )

            transition = Transition(
                from_state="INIT",
                to_state="PLANNING",
                requires=RequiresBlock(
                    inputs_present=True,
                    artifacts=(artifact_name,),
                    human_approval=(artifact_name,),
                    conditions={"id": "IP-1"},
                ),
                notes=None,
            )
            schemas = {
                "implementation_plan": load_schema(
                    self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
                )
            }
            gate = self.evaluator.evaluate(
                transition=transition,
                project_root=root,
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertEqual(
                [c.check_type for c in gate.checks],
                [
                    CheckType.INPUT_PRESENCE,
                    CheckType.INPUT_PRESENCE,
                    CheckType.INPUT_PRESENCE,
                    CheckType.INPUT_PRESENCE,
                    CheckType.INPUT_PRESENCE,
                    CheckType.ARTIFACT_PRESENCE,
                    CheckType.APPROVAL,
                    CheckType.CONDITION,
                ],
            )
            self.assertEqual(gate.result, CheckResult.PASS)

    def test_approval_requires_matching_hash_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0002" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            artifact_name = "implementation_plan.yaml"
            artifact_path = artifacts / artifact_name
            artifact_path.write_text(
                "id: IP-2\n"
                "supersedes_id: null\n"
                "created_at: '2026-03-14T10:00:00Z'\n"
                "inputs:\n"
                "  change_intent_id: CI-2\n"
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
            (artifacts.parent / "decision_log.yaml").write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D2\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: bob\n"
                "    decision: approve\n"
                "    scope: implementation\n"
                "    references:\n"
                f"      - artifact: {artifact_name}\n"
                "        artifact_id: IP-2\n"
                "        artifact_hash: deadbeef\n"
                "    rationale: approved\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            schemas = {
                "implementation_plan": load_schema(
                    self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
                )
            }
            details = self.evaluator.check_approval(
                artifacts_dir=artifacts,
                decision_log_path=artifacts.parent / "decision_log.yaml",
                artifact_names=[artifact_name],
                schemas=schemas,
            )
            self.assertEqual(len(details), 1)
            self.assertEqual(details[0].result, CheckResult.FAIL)

    def test_condition_comparison_is_case_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0003" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "review_result.md").write_text(
                "id: RR-1\n"
                "supersedes_id: null\n"
                "outcome: ACCEPTED\n"
                "\n"
                "## Summary\nok\n",
                encoding="utf-8",
            )
            schemas = {
                "review_result": load_schema(
                    self.repo_root / "artifacts" / "schemas" / "review_result.schema.md"
                )
            }
            details = self.evaluator.check_conditions(
                artifacts_dir=artifacts,
                conditions={"review_outcome": "accepted"},
                schemas=schemas,
            )
            self.assertEqual(details[0].result, CheckResult.FAIL)
            self.assertIn("expected 'accepted'", details[0].detail or "")

    def test_decision_log_reject_for_passes_when_reject_entry_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0004" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            release_metadata = artifacts / "release_metadata.json"
            release_metadata.write_text(
                "{\n"
                '  "id": "RM-1",\n'
                '  "supersedes_id": null,\n'
                '  "created_at": "2026-03-14T10:00:00Z",\n'
                '  "run_id": "RUN-20260314-0004",\n'
                '  "inputs": {\n'
                '    "review_result_ref": "RR-1",\n'
                '    "review_result_hash": null,\n'
                '    "test_report_run_id": "RUN-20260314-0004",\n'
                '    "implementation_plan_id": "IP-1"\n'
                "  },\n"
                '  "artifacts": [{"name": "review_result.md", "ref": "RR-1", "hash": null}],\n'
                '  "environment": {"os": "win32", "tool_versions": {"python": "3.14"}}\n'
                "}\n",
                encoding="utf-8",
            )
            (artifacts.parent / "decision_log.yaml").write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D-4\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: bob\n"
                "    decision: reject\n"
                "    scope: release\n"
                "    references:\n"
                "      - artifact: release_metadata.json\n"
                "        artifact_id: RM-1\n"
                "        artifact_hash: deadbeef\n"
                "    rationale: blocked\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            schemas = {
                "release_metadata": load_schema(
                    self.repo_root / "artifacts" / "schemas" / "release_metadata.schema.json"
                )
            }
            details = self.evaluator.check_conditions(
                artifacts_dir=artifacts,
                conditions={"decision_log_reject_for": "release_metadata.json"},
                schemas=schemas,
                decision_log_path=artifacts.parent / "decision_log.yaml",
            )
            self.assertEqual(details[0].result, CheckResult.PASS)

    def test_note_condition_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "runs" / "RUN-20260314-0005" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            details = self.evaluator.check_conditions(
                artifacts_dir=artifacts,
                conditions={"note": "human readable text"},
                schemas={},
                decision_log_path=artifacts.parent / "decision_log.yaml",
            )
            self.assertEqual(details, [])


if __name__ == "__main__":
    unittest.main()

