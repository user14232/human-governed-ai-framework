from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.artifacts.artifact_system import (
    ArtifactSystem,
    ArtifactStructureError,
    ImmutableArtifactError,
)
from runtime.framework.schema_loader import load_schema
from runtime.types.run import RunContext
from runtime.types.workflow import WorkflowDefinition


class ArtifactSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.system = ArtifactSystem()
        self.workflow = WorkflowDefinition(
            workflow_id="default_workflow",
            version="v1",
            states=("INIT",),
            transitions=(),
            artifacts_used=(),
        )

    def test_validate_markdown_structure_success(self) -> None:
        schema = load_schema(
            self.repo_root / "artifacts" / "schemas" / "implementation_summary.schema.md"
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "implementation_summary.md"
            path.write_text(
                "id: IMP-1\n"
                "supersedes_id: null\n"
                "\n"
                "## Summary\nx\n"
                "## Inputs\nx\n"
                "## Files changed\nx\n"
                "## Plan mapping\nx\n"
                "## Deviations (if any)\nx\n"
                "## Follow-ups (optional)\nx\n",
                encoding="utf-8",
            )
            result = self.system.validate_structure(path, schema)
            self.assertTrue(result.valid)

    def test_validate_markdown_structure_failure(self) -> None:
        schema = load_schema(self.repo_root / "artifacts" / "schemas" / "review_result.schema.md")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "review_result.md"
            path.write_text(
                "id: RR-1\n"
                "supersedes_id: null\n"
                "outcome: ACCEPTED\n"
                "\n"
                "## Summary\nx\n",
                encoding="utf-8",
            )
            result = self.system.validate_structure(path, schema)
            self.assertFalse(result.valid)
            self.assertTrue(any("Missing required markdown section" in e for e in result.errors))

    def test_register_yaml_artifact(self) -> None:
        schema = load_schema(
            self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
        )
        schemas = {"implementation_plan": schema}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts_dir = root / "runs" / "RUN-20260314-0001" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifacts_dir / "implementation_plan.yaml"
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
                "non_goals:\n"
                "  - ng-1\n"
                "risks:\n"
                "  - r-1\n",
                encoding="utf-8",
            )
            ctx = RunContext(
                run_id="RUN-20260314-0001",
                project_root=root,
                run_dir=artifacts_dir.parent,
                artifacts_dir=artifacts_dir,
                workflow_def=self.workflow,
                current_state="INIT",
            )
            ref = self.system.register(ctx, "implementation_plan.yaml", "agent_planner", schemas)
            self.assertEqual(ref.artifact_id, "IP-1")
            self.assertIsNotNone(ref.artifact_hash)

    def test_register_rejects_invalid_structure(self) -> None:
        schema = load_schema(
            self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
        )
        schemas = {"implementation_plan": schema}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts_dir = root / "runs" / "RUN-20260314-0002" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "implementation_plan.yaml").write_text("id: IP-2\n", encoding="utf-8")
            ctx = RunContext(
                run_id="RUN-20260314-0002",
                project_root=root,
                run_dir=artifacts_dir.parent,
                artifacts_dir=artifacts_dir,
                workflow_def=self.workflow,
                current_state="INIT",
            )
            with self.assertRaises(ArtifactStructureError):
                self.system.register(ctx, "implementation_plan.yaml", "agent_planner", schemas)

    def test_register_rejects_empty_required_list_fields(self) -> None:
        schema = load_schema(
            self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
        )
        schemas = {"implementation_plan": schema}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts_dir = root / "runs" / "RUN-20260314-0004" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            (artifacts_dir / "implementation_plan.yaml").write_text(
                "id: IP-3\n"
                "supersedes_id: null\n"
                "created_at: '2026-03-14T10:00:00Z'\n"
                "inputs:\n"
                "  change_intent_id: CI-1\n"
                "  architecture_contract_ref: architecture_contract.md\n"
                "plan_items: []\n"
                "non_goals: []\n"
                "risks: []\n",
                encoding="utf-8",
            )
            ctx = RunContext(
                run_id="RUN-20260314-0004",
                project_root=root,
                run_dir=artifacts_dir.parent,
                artifacts_dir=artifacts_dir,
                workflow_def=self.workflow,
                current_state="INIT",
            )
            with self.assertRaises(ArtifactStructureError):
                self.system.register(ctx, "implementation_plan.yaml", "agent_planner", schemas)

    def test_check_immutability_and_supersede(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts_dir = root / "runs" / "RUN-20260314-0003" / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            artifact_name = "review_result.md"
            artifact_path = artifacts_dir / artifact_name
            artifact_path.write_text(
                "id: RR-100\nsupersedes_id: null\noutcome: ACCEPTED\n\n## Summary\nok\n",
                encoding="utf-8",
            )
            decision_log = artifacts_dir.parent / "decision_log.yaml"
            decision_log.write_text(
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: D1\n"
                "    timestamp: '2026-03-14T11:00:00Z'\n"
                "    human_identity: alice\n"
                "    decision: approve\n"
                "    scope: review\n"
                "    references:\n"
                "      - artifact: review_result.md\n"
                "        artifact_id: RR-100\n"
                "        artifact_hash: null\n"
                "    rationale: ok\n"
                "    supersedes_decision_id: null\n",
                encoding="utf-8",
            )
            self.assertTrue(self.system.check_immutability("RR-100", decision_log))

            ctx = RunContext(
                run_id="RUN-20260314-0003",
                project_root=root,
                run_dir=artifacts_dir.parent,
                artifacts_dir=artifacts_dir,
                workflow_def=self.workflow,
                current_state="REVIEWING",
            )
            with self.assertRaises(ImmutableArtifactError):
                self.system.supersede(ctx, artifact_name, decision_log)

            # Non-approved artifact can be superseded deterministically.
            artifact_path.write_text(
                "id: RR-200\nsupersedes_id: null\noutcome: FAILED\n\n## Summary\nok\n",
                encoding="utf-8",
            )
            res = self.system.supersede(ctx, artifact_name, decision_log)
            self.assertEqual(res.version_number, 1)
            self.assertTrue(res.versioned_path.name.endswith(".v1.md"))


if __name__ == "__main__":
    unittest.main()

