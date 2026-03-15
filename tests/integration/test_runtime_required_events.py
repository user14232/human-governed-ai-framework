from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_runtime.invocation_layer import AgentInvocationLayer, InvocationMode
from kernel.cli import RuntimeCLI
from kernel.engine.gate_evaluator import GateEvaluator
from kernel.framework.agent_loader import AgentContract
from kernel.framework.schema_loader import load_all_schemas, load_schema
from kernel.engine.run_engine import RunEngine
from kernel.engine.workflow_engine import WorkflowEngine
from kernel.store.run_store import run_metrics_path
from kernel.types.run import RunContext


class RuntimeRequiredEventsIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_advance_pass_path_emits_required_workflow_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._prepare_project(root, include_required_inputs=True)
            run_engine = RunEngine()
            ctx = run_engine.initialize_run(root, root / "change_intent.yaml", "delivery_workflow")
            wf_engine = WorkflowEngine(ctx.workflow_def)
            schemas = load_all_schemas(root / "artifacts" / "schemas")

            result = wf_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(result.transitioned)

            payload = self._load_metrics(root, ctx.run_id)
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertIn("workflow.transition_checked", event_types)
            self.assertIn("workflow.transition_completed", event_types)

    def test_advance_blocked_path_emits_run_blocked_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._prepare_project(root, include_required_inputs=True)
            run_engine = RunEngine()
            ctx = run_engine.initialize_run(root, root / "change_intent.yaml", "delivery_workflow")
            wf_engine = WorkflowEngine(ctx.workflow_def)
            schemas = load_all_schemas(root / "artifacts" / "schemas")

            first = wf_engine.advance(
                ctx=ctx,
                evaluator=GateEvaluator(),
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertTrue(first.transitioned)
            self.assertEqual(first.new_state, "PLANNING")

            blocked_ctx = RunContext(
                run_id=ctx.run_id,
                project_root=ctx.project_root,
                run_dir=ctx.run_dir,
                artifacts_dir=ctx.artifacts_dir,
                workflow_def=ctx.workflow_def,
                current_state=first.new_state or ctx.current_state,
            )
            result = wf_engine.advance(
                ctx=blocked_ctx,
                evaluator=GateEvaluator(),
                decision_log_path=ctx.run_dir / "decision_log.yaml",
                schemas=schemas,
            )
            self.assertFalse(result.transitioned)

            payload = self._load_metrics(root, ctx.run_id)
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertIn("workflow.transition_checked", event_types)
            self.assertIn("run.blocked", event_types)
            blocked_event = next(event for event in payload["events"] if event.get("event_type") == "run.blocked")
            blocked_payload = blocked_event["payload"]
            self.assertEqual(blocked_payload["blocking_reason"], "missing_artifact")
            self.assertTrue(isinstance(blocked_payload["missing_artifacts"], list))

    def test_invocation_path_emits_required_invocation_and_artifact_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._prepare_project(root, include_required_inputs=True)
            cli = RuntimeCLI()
            base_ctx = cli.run(root, root / "change_intent.yaml", "delivery_workflow")
            ctx = RunContext(
                run_id=base_ctx.run_id,
                project_root=base_ctx.project_root,
                run_dir=base_ctx.run_dir,
                artifacts_dir=base_ctx.artifacts_dir,
                workflow_def=base_ctx.workflow_def,
                current_state="IMPLEMENTING",
            )

            # Invocation contracts are explicit and deterministic for this integration path.
            contract = AgentContract(
                role_id="agent_implementer",
                input_artifacts=("implementation_plan.yaml",),
                output_artifacts=("implementation_summary.md",),
                owned_artifacts=("implementation_summary.md",),
                workflow_states=("IMPLEMENTING",),
            )
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: PLAN-1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text(
                "id: IS-1\n"
                "supersedes_id: null\n"
                "\n"
                "## Summary\nok\n"
                "## Inputs\nok\n"
                "## Files changed\nok\n"
                "## Plan mapping\nok\n"
                "## Deviations (if any)\nnone\n"
                "## Follow-ups (optional)\nnone\n",
                encoding="utf-8",
            )
            schemas = {
                "implementation_summary": load_schema(
                    self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_summary.schema.md"
                )
            }

            layer = AgentInvocationLayer()
            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_implementer",
                agent_contracts={"agent_implementer": contract},
                schemas=schemas,
                mode=InvocationMode.HUMAN_AS_AGENT,
            )
            self.assertEqual(result.outcome.value, "completed")

            payload = self._load_metrics(root, ctx.run_id)
            event_types = [event.get("event_type") for event in payload.get("events", [])]
            self.assertIn("agent.invocation_started", event_types)
            self.assertIn("artifact.created", event_types)
            self.assertIn("agent.invocation_completed", event_types)

    def _prepare_project(self, root: Path, include_required_inputs: bool) -> None:
        (root / "workflow").mkdir(parents=True, exist_ok=True)
        (root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
        (root / "workflow" / "delivery_workflow.yaml").write_text(
            (self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "artifacts" / "schemas" / "implementation_plan.schema.yaml").write_text(
            (self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_plan.schema.yaml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        (root / "change_intent.yaml").write_text("id: CI-1\n", encoding="utf-8")
        if include_required_inputs:
            for name in (
                "domain_scope.md",
                "domain_rules.md",
                "source_policy.md",
                "glossary.md",
                "architecture_contract.md",
            ):
                (root / name).write_text("ok\n", encoding="utf-8")

    def _load_metrics(self, project_root: Path, run_id: str) -> dict:
        metrics = run_metrics_path(project_root / "runs" / run_id)
        return json.loads(metrics.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
