from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile

from runtime.engine.gate_evaluator import GateEvaluator
from runtime.engine.run_engine import RunEngine
from runtime.engine.workflow_engine import WorkflowEngine
from runtime.framework.schema_loader import load_all_schemas
from runtime.store.run_store import run_metrics_path
from runtime.types.run import RunContext


class SecondaryWorkflowsEndToEndIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_improvement_cycle_workflow_advances_to_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            self._prepare_project(
                project_root=project_root,
                workflows=("improvement_cycle",),
                schema_files=(
                    "review_result.schema.md",
                    "reflection_notes.schema.md",
                    "improvement_proposal.schema.md",
                    "decision_log.schema.yaml",
                ),
            )
            run_engine = RunEngine()
            ctx = run_engine.initialize_run(project_root, project_root / "change_intent.yaml", "improvement_cycle")
            workflow_engine = WorkflowEngine(ctx.workflow_def)
            schemas = load_all_schemas(project_root / "artifacts" / "schemas")

            artifacts_dir = ctx.artifacts_dir
            run_dir = ctx.run_dir
            (artifacts_dir / "test_report.json").write_text("{}", encoding="utf-8")
            (artifacts_dir / "review_result.md").write_text(
                "id: RR-IC-1\n"
                "supersedes_id: null\n"
                "outcome: ACCEPTED\n"
                "\n"
                "## Summary\nok\n"
                "## Outcome\nACCEPTED\n"
                "## Evidence\nok\n"
                "## Findings\nnone\n",
                encoding="utf-8",
            )

            step_1 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_1.transitioned)
            self.assertEqual(step_1.new_state, "REFLECT")
            ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=step_1.new_state or ctx.current_state,
            )

            (artifacts_dir / "reflection_notes.md").write_text(
                "id: RN-IC-1\n"
                "supersedes_id: null\n"
                "\n"
                "## Evidence referenced\n"
                "- run_metrics.json\n"
                "- test_report.json\n"
                "- review_result.md\n"
                "## Observations (facts)\n"
                "- Stable baseline.\n"
                "## Hypotheses (explicitly labeled)\n"
                "- Hypothesis: reduce rework.\n"
                "## Open questions\n"
                "- none\n",
                encoding="utf-8",
            )
            step_2 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_2.transitioned)
            self.assertEqual(step_2.new_state, "PROPOSE")
            ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=step_2.new_state or ctx.current_state,
            )

            (artifacts_dir / "improvement_proposal.md").write_text(
                "id: IPROP-IC-1\n"
                "supersedes_id: null\n"
                "\n"
                "## 1) Problem statement (evidence-cited)\n"
                "- Reflection references the current bottleneck.\n"
                "## 2) Proposed change\n"
                "- Add deterministic stage verification.\n"
                "## 3) Expected impact\n"
                "- Better auditability.\n"
                "## 4) Risks and mitigations\n"
                "- Keep rollback path explicit.\n"
                "## 5) Required human decisions\n"
                "- Approve proposal execution in next run.\n"
                "## 6) Decision reference\n"
                "- DEC-IC-1\n",
                encoding="utf-8",
            )
            approval_log = (
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: DEC-IC-1\n"
                "    timestamp: '2026-03-14T10:00:00Z'\n"
                "    human_identity: phili\n"
                "    decision: approve\n"
                "    scope: improvement_cycle\n"
                "    references:\n"
                "      - artifact: improvement_proposal.md\n"
                "        artifact_id: IPROP-IC-1\n"
                "        artifact_hash: ''\n"
                "    rationale: approved\n"
                "    supersedes_decision_id: null\n"
            )
            (run_dir / "decision_log.yaml").write_text(approval_log, encoding="utf-8")
            (artifacts_dir / "decision_log.yaml").write_text(approval_log, encoding="utf-8")

            step_3 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_3.transitioned)
            self.assertEqual(step_3.new_state, "HUMAN_DECISION")

            metrics = self._load_metrics(project_root, ctx.run_id)
            to_states = self._completed_to_states(metrics)
            self.assertEqual(to_states, ["REFLECT", "PROPOSE", "HUMAN_DECISION"])

    def test_release_workflow_advances_to_released(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            self._prepare_project(
                project_root=project_root,
                workflows=("release_workflow",),
                schema_files=(
                    "review_result.schema.md",
                    "release_notes.schema.md",
                    "release_metadata.schema.json",
                    "decision_log.schema.yaml",
                ),
            )
            run_engine = RunEngine()
            ctx = run_engine.initialize_run(project_root, project_root / "change_intent.yaml", "release_workflow")
            workflow_engine = WorkflowEngine(ctx.workflow_def)
            schemas = load_all_schemas(project_root / "artifacts" / "schemas")

            artifacts_dir = ctx.artifacts_dir
            run_dir = ctx.run_dir
            (artifacts_dir / "review_result.md").write_text(
                "id: RR-RW-1\n"
                "supersedes_id: null\n"
                "outcome: ACCEPTED\n"
                "\n"
                "## Summary\nok\n"
                "## Outcome\nACCEPTED\n"
                "## Evidence\nok\n"
                "## Findings\nnone\n",
                encoding="utf-8",
            )
            (artifacts_dir / "test_report.json").write_text("{}", encoding="utf-8")
            empty_log = "schema_version: v1\ndecisions: []\n"
            (run_dir / "decision_log.yaml").write_text(empty_log, encoding="utf-8")
            (artifacts_dir / "decision_log.yaml").write_text(empty_log, encoding="utf-8")

            step_1 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_1.transitioned)
            self.assertEqual(step_1.new_state, "RELEASE_PREPARING")
            ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=step_1.new_state or ctx.current_state,
            )

            (artifacts_dir / "release_notes.md").write_text(
                "id: RN-RW-1\n"
                "supersedes_id: null\n"
                "\n"
                "## Release summary\n"
                "- Deterministic release candidate.\n"
                "## Evidence\n"
                "- review_result.md\n"
                "- test_report.json\n"
                "## Changes included\n"
                "- Scope A\n"
                "## Known issues / debt\n"
                "- none\n",
                encoding="utf-8",
            )
            (artifacts_dir / "release_metadata.json").write_text(
                "{\n"
                '  "id": "RM-RW-1",\n'
                '  "supersedes_id": null,\n'
                '  "created_at": "2026-03-14T09:00:00Z",\n'
                f'  "run_id": "{ctx.run_id}",\n'
                '  "inputs": {\n'
                '    "review_result_ref": "RR-RW-1",\n'
                '    "review_result_hash": null,\n'
                '    "test_report_run_id": "RUN-TEST",\n'
                '    "implementation_plan_id": "IP-RW-1"\n'
                "  },\n"
                '  "artifacts": [{"name": "review_result.md", "ref": "RR-RW-1", "hash": null}],\n'
                '  "environment": {"os": "win32", "tool_versions": {"python": "3.14"}}\n'
                "}\n",
                encoding="utf-8",
            )
            approval_log = (
                "schema_version: v1\n"
                "decisions:\n"
                "  - decision_id: DEC-RW-1\n"
                "    timestamp: '2026-03-14T10:00:00Z'\n"
                "    human_identity: phili\n"
                "    decision: approve\n"
                "    scope: release\n"
                "    references:\n"
                "      - artifact: release_metadata.json\n"
                "        artifact_id: RM-RW-1\n"
                "        artifact_hash: ''\n"
                "    rationale: approved\n"
                "    supersedes_decision_id: null\n"
            )
            (run_dir / "decision_log.yaml").write_text(approval_log, encoding="utf-8")
            (artifacts_dir / "decision_log.yaml").write_text(approval_log, encoding="utf-8")

            step_2 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_2.transitioned)
            self.assertEqual(step_2.new_state, "RELEASE_REVIEW")
            ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=step_2.new_state or ctx.current_state,
            )

            step_3 = workflow_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(step_3.transitioned)
            self.assertEqual(step_3.new_state, "RELEASED")

            metrics = self._load_metrics(project_root, ctx.run_id)
            to_states = self._completed_to_states(metrics)
            self.assertEqual(to_states, ["RELEASE_PREPARING", "RELEASE_REVIEW", "RELEASED"])

    def _prepare_project(
        self,
        project_root: Path,
        workflows: tuple[str, ...],
        schema_files: tuple[str, ...],
    ) -> None:
        (project_root / "workflow").mkdir(parents=True, exist_ok=True)
        (project_root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
        for workflow_name in workflows:
            copyfile(
                self.repo_root / "framework" / "workflows" / f"{workflow_name}.yaml",
                project_root / "workflow" / f"{workflow_name}.yaml",
            )
        for schema_file in schema_files:
            copyfile(
                self.repo_root / "framework" / "artifacts" / "schemas" / schema_file,
                project_root / "artifacts" / "schemas" / schema_file,
            )
        (project_root / "change_intent.yaml").write_text("id: CI-1\n", encoding="utf-8")

    def _load_metrics(self, project_root: Path, run_id: str) -> dict:
        return json.loads(
            run_metrics_path(project_root / "runs" / run_id).read_text(encoding="utf-8")
        )

    def _completed_to_states(self, metrics: dict) -> list[str]:
        states: list[str] = []
        for event in metrics.get("events", []):
            if event.get("event_type") != "workflow.transition_completed":
                continue
            payload = event.get("payload", {})
            to_state = payload.get("to_state")
            if isinstance(to_state, str):
                states.append(to_state)
        return states


if __name__ == "__main__":
    unittest.main()
