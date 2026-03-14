from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.artifacts.artifact_system import ArtifactStructureError, ArtifactSystem
from runtime.agents.invocation_layer import (
    AgentInvocationLayer,
    InvocationMode,
    MissingAdapterError,
    SingleShotViolationError,
    UnexpectedAdapterOutputError,
)
from runtime.framework.schema_loader import load_schema
from runtime.store.run_store import run_metrics_path
from runtime.framework.agent_loader import AgentContract
from runtime.types.artifact import ArtifactRef
from runtime.types.run import RunContext
from runtime.types.workflow import WorkflowDefinition


class _FakeArtifactSystem:
    def __init__(self) -> None:
        self.register_calls: list[tuple[str, str]] = []

    def register(self, ctx: RunContext, artifact_name: str, owner_role: str, schemas: dict):  # type: ignore[no-untyped-def]
        _ = ctx
        _ = schemas
        self.register_calls.append((artifact_name, owner_role))
        return ArtifactRef(name=artifact_name, artifact_id=f"id-{artifact_name}", artifact_hash="h")


class _FakeAdapter:
    def __init__(self, outputs: dict[str, Path]) -> None:
        self.outputs = outputs
        self.last_inputs: dict[str, Path] | None = None
        self.last_output_dir: Path | None = None

    def invoke(self, input_paths: dict[str, Path], output_dir: Path) -> dict[str, Path]:
        self.last_inputs = input_paths
        self.last_output_dir = output_dir
        return self.outputs


class InvocationLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WorkflowDefinition(
            workflow_id="wf",
            version="v1",
            states=("IMPLEMENTING",),
            transitions=(),
            artifacts_used=(),
        )
        self.contract = AgentContract(
            role_id="agent_implementer",
            input_artifacts=("implementation_plan.yaml",),
            output_artifacts=("implementation_summary.md",),
            owned_artifacts=("implementation_summary.md",),
            workflow_states=("IMPLEMENTING",),
        )

    def test_automated_mode_dispatches_adapter_and_registers_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            input_path = ctx.artifacts_dir / "implementation_plan.yaml"
            output_path = ctx.artifacts_dir / "implementation_summary.md"
            input_path.write_text("id: p1\n", encoding="utf-8")
            output_path.write_text("id: s1\n", encoding="utf-8")

            fake_artifacts = _FakeArtifactSystem()
            adapter = _FakeAdapter(outputs={"implementation_summary.md": output_path})
            layer = AgentInvocationLayer(artifact_system=fake_artifacts)  # type: ignore[arg-type]

            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_implementer",
                agent_contracts={"agent_implementer": self.contract},
                schemas={},
                mode=InvocationMode.AUTOMATED,
                adapter=adapter,
            )

            self.assertEqual(result.outcome.value, "completed")
            self.assertEqual(adapter.last_inputs, {"implementation_plan.yaml": input_path})
            self.assertEqual(adapter.last_output_dir, ctx.artifacts_dir)
            self.assertEqual(fake_artifacts.register_calls, [("implementation_summary.md", "agent_implementer")])
            self.assertEqual(len(result.output_refs), 1)
            self.assertEqual(result.output_refs[0].name, "implementation_summary.md")
            self.assertEqual(result.invocation_record["agent_role"], "agent_implementer")
            self.assertEqual(result.invocation_record["workflow_state"], "IMPLEMENTING")
            self.assertEqual(result.invocation_record["mode"], "automated")
            self.assertEqual(len(result.invocation_record["inputs"]), 1)
            self.assertEqual(len(result.invocation_record["outputs"]), 1)

            metrics = json.loads(run_metrics_path(ctx.run_dir).read_text(encoding="utf-8"))
            self.assertEqual(len(metrics["invocation_records"]), 1)
            self.assertEqual(metrics["invocation_records"][0]["agent_role"], "agent_implementer")
            event_types = [event.get("event_type") for event in metrics.get("events", [])]
            self.assertEqual(
                event_types,
                ["agent.invocation_started", "artifact.created", "agent.invocation_completed"],
            )
            self.assertEqual(metrics["events"][0]["payload"]["agent_role"], "agent_implementer")
            self.assertEqual(metrics["events"][1]["payload"]["artifact_name"], "implementation_summary.md")
            self.assertEqual(metrics["events"][2]["payload"]["outcome"], "completed")

    def test_human_mode_uses_declared_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: p1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text("id: s1\n", encoding="utf-8")

            fake_artifacts = _FakeArtifactSystem()
            layer = AgentInvocationLayer(artifact_system=fake_artifacts)  # type: ignore[arg-type]

            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_implementer",
                agent_contracts={"agent_implementer": self.contract},
                schemas={},
                mode=InvocationMode.HUMAN_AS_AGENT,
                adapter=None,
            )

            self.assertEqual(result.outcome.value, "completed")
            self.assertEqual(fake_artifacts.register_calls, [("implementation_summary.md", "agent_implementer")])

    def test_automated_mode_requires_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: p1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text("id: s1\n", encoding="utf-8")

            layer = AgentInvocationLayer(artifact_system=_FakeArtifactSystem())  # type: ignore[arg-type]
            with self.assertRaises(MissingAdapterError):
                layer.invoke(
                    ctx=ctx,
                    agent_role="agent_implementer",
                    agent_contracts={"agent_implementer": self.contract},
                    schemas={},
                    mode=InvocationMode.AUTOMATED,
                    adapter=None,
                )

    def test_automated_mode_rejects_undeclared_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: p1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text("id: s1\n", encoding="utf-8")
            (ctx.artifacts_dir / "other.md").write_text("id: x\n", encoding="utf-8")

            layer = AgentInvocationLayer(artifact_system=_FakeArtifactSystem())  # type: ignore[arg-type]
            adapter = _FakeAdapter(outputs={"other.md": ctx.artifacts_dir / "other.md"})
            with self.assertRaises(UnexpectedAdapterOutputError):
                layer.invoke(
                    ctx=ctx,
                    agent_role="agent_implementer",
                    agent_contracts={"agent_implementer": self.contract},
                    schemas={},
                    mode=InvocationMode.AUTOMATED,
                    adapter=adapter,
                )

    def test_single_shot_blocks_duplicate_without_rework(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: p1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text("id: s1\n", encoding="utf-8")
            metrics_path = run_metrics_path(ctx.run_dir)
            metrics_path.write_text(
                json.dumps(
                    {
                        "run_metadata": {},
                        "events": [],
                        "invocation_records": [
                            {
                                "agent_role": "agent_implementer",
                                "workflow_state": "IMPLEMENTING",
                                "invoked_at": "2026-03-14T17:00:00+00:00",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            layer = AgentInvocationLayer(artifact_system=_FakeArtifactSystem())  # type: ignore[arg-type]
            adapter = _FakeAdapter(outputs={"implementation_summary.md": ctx.artifacts_dir / "implementation_summary.md"})
            with self.assertRaises(SingleShotViolationError):
                layer.invoke(
                    ctx=ctx,
                    agent_role="agent_implementer",
                    agent_contracts={"agent_implementer": self.contract},
                    schemas={},
                    mode=InvocationMode.AUTOMATED,
                    adapter=adapter,
                )

    def test_single_shot_allows_reinvoke_after_rework_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            (ctx.artifacts_dir / "implementation_plan.yaml").write_text("id: p1\n", encoding="utf-8")
            (ctx.artifacts_dir / "implementation_summary.md").write_text("id: s1\n", encoding="utf-8")
            metrics_path = run_metrics_path(ctx.run_dir)
            metrics_path.write_text(
                json.dumps(
                    {
                        "run_metadata": {},
                        "events": [
                            {
                                "event_type": "run.rework_started",
                                "timestamp": "2026-03-14T17:10:00+00:00",
                            }
                        ],
                        "invocation_records": [
                            {
                                "agent_role": "agent_implementer",
                                "workflow_state": "IMPLEMENTING",
                                "invoked_at": "2026-03-14T17:00:00+00:00",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fake_artifacts = _FakeArtifactSystem()
            layer = AgentInvocationLayer(artifact_system=fake_artifacts)  # type: ignore[arg-type]
            adapter = _FakeAdapter(outputs={"implementation_summary.md": ctx.artifacts_dir / "implementation_summary.md"})

            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_implementer",
                agent_contracts={"agent_implementer": self.contract},
                schemas={},
                mode=InvocationMode.AUTOMATED,
                adapter=adapter,
            )
            self.assertEqual(result.outcome.value, "completed")
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            self.assertEqual(len(metrics["invocation_records"]), 2)

    def test_invoke_with_real_artifact_system_registers_hash_and_validates_structure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            input_path = ctx.artifacts_dir / "implementation_plan.yaml"
            output_path = ctx.artifacts_dir / "implementation_summary.md"
            input_path.write_text("id: p1\n", encoding="utf-8")
            output_path.write_text(
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
            repo_root = Path(__file__).resolve().parents[2]
            schemas = {
                "implementation_summary": load_schema(
                    repo_root / "artifacts" / "schemas" / "implementation_summary.schema.md"
                )
            }
            layer = AgentInvocationLayer(artifact_system=ArtifactSystem())
            adapter = _FakeAdapter(outputs={"implementation_summary.md": output_path})
            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_implementer",
                agent_contracts={"agent_implementer": self.contract},
                schemas=schemas,
                mode=InvocationMode.AUTOMATED,
                adapter=adapter,
            )
            self.assertEqual(result.outcome.value, "completed")
            self.assertEqual(result.output_refs[0].artifact_id, "IS-1")
            self.assertIsNotNone(result.output_refs[0].artifact_hash)

    def test_invoke_with_real_artifact_system_rejects_invalid_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ctx = self._make_context(Path(td))
            input_path = ctx.artifacts_dir / "implementation_plan.yaml"
            output_path = ctx.artifacts_dir / "implementation_summary.md"
            input_path.write_text("id: p1\n", encoding="utf-8")
            # Missing required sections by schema.
            output_path.write_text("id: IS-2\nsupersedes_id: null\n\n## Summary\nonly\n", encoding="utf-8")
            repo_root = Path(__file__).resolve().parents[2]
            schemas = {
                "implementation_summary": load_schema(
                    repo_root / "artifacts" / "schemas" / "implementation_summary.schema.md"
                )
            }
            layer = AgentInvocationLayer(artifact_system=ArtifactSystem())
            adapter = _FakeAdapter(outputs={"implementation_summary.md": output_path})
            with self.assertRaises(ArtifactStructureError):
                layer.invoke(
                    ctx=ctx,
                    agent_role="agent_implementer",
                    agent_contracts={"agent_implementer": self.contract},
                    schemas=schemas,
                    mode=InvocationMode.AUTOMATED,
                    adapter=adapter,
                )

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
            current_state="IMPLEMENTING",
        )


if __name__ == "__main__":
    unittest.main()

