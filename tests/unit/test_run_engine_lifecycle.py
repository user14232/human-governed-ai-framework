from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.engine.run_engine import (
    InvalidTerminalStateError,
    MissingInputError,
    RunEngine,
    StateReconstructionError,
)


class RunEngineLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RunEngine()
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_initialize_run_creates_directory_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            (project_root / "workflow").mkdir(parents=True, exist_ok=True)
            (project_root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = project_root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")

            ctx = self.engine.initialize_run(project_root, change_intent)
            self.assertTrue(ctx.run_dir.is_dir())
            self.assertTrue((ctx.artifacts_dir / "change_intent.yaml").is_file())
            self.assertEqual(ctx.current_state, "INIT")
            self.assertRegex(ctx.run_id, r"^RUN-\d{8}-\d{4}$")

    def test_initialize_run_uses_workflow_declared_initial_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            (project_root / "workflow").mkdir(parents=True, exist_ok=True)
            (project_root / "workflow" / "improvement_cycle.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "improvement_cycle.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = project_root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")

            ctx = self.engine.initialize_run(
                project_root,
                change_intent,
                workflow_name="improvement_cycle",
            )
            self.assertEqual(ctx.current_state, "OBSERVE")

    def test_initialize_run_missing_input_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with self.assertRaises(MissingInputError):
                self.engine.initialize_run(root, root / "missing_change_intent.yaml")

    def test_resume_run_reconstructs_state_from_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "RUN-20260314-0001"
            run_artifacts = root / "runs" / run_id / "artifacts"
            run_artifacts.mkdir(parents=True, exist_ok=True)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (run_artifacts / "run_metrics.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "event_type": "workflow.transition_completed",
                                "payload": {"to_state": "PLANNING"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            ctx = self.engine.resume_run(root, run_id)
            self.assertEqual(ctx.current_state, "PLANNING")
            self.assertEqual(ctx.run_id, run_id)

    def test_resume_run_invalid_metrics_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "RUN-20260314-0002"
            run_artifacts = root / "runs" / run_id / "artifacts"
            run_artifacts.mkdir(parents=True, exist_ok=True)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (run_artifacts / "run_metrics.json").write_text("{bad json", encoding="utf-8")
            with self.assertRaises(StateReconstructionError):
                self.engine.resume_run(root, run_id)

    def test_initialize_run_uses_canonical_inputs_root_when_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            (project_root / "workflow").mkdir(parents=True, exist_ok=True)
            (project_root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = project_root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")
            canonical = project_root / ".devOS" / "project_inputs"
            canonical.mkdir(parents=True, exist_ok=True)

            ctx = self.engine.initialize_run(project_root, change_intent)
            self.assertEqual(ctx.project_inputs_root, canonical.resolve())

    def test_initialize_run_falls_back_to_project_root_without_canonical_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            (project_root / "workflow").mkdir(parents=True, exist_ok=True)
            (project_root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = project_root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")

            ctx = self.engine.initialize_run(project_root, change_intent)
            self.assertEqual(ctx.project_inputs_root, project_root.resolve())

    def test_initialize_run_explicit_project_inputs_root_overrides_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            (project_root / "workflow").mkdir(parents=True, exist_ok=True)
            (project_root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = project_root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")
            explicit_root = project_root / "custom_inputs"
            explicit_root.mkdir(parents=True, exist_ok=True)
            # canonical dir also exists — explicit arg must win
            (project_root / ".devOS" / "project_inputs").mkdir(parents=True, exist_ok=True)

            ctx = self.engine.initialize_run(
                project_root,
                change_intent,
                project_inputs_root=explicit_root,
            )
            self.assertEqual(ctx.project_inputs_root, explicit_root.resolve())

    def test_declare_terminal_validates_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "default_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")
            ctx = self.engine.initialize_run(root, change_intent)

            self.engine.declare_terminal(ctx, "ACCEPTED")
            metrics = ctx.run_dir / "artifacts" / "run_metrics.json"
            payload = json.loads(metrics.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(payload.get("events", [])), 2)
            event_types = [e.get("event_type") for e in payload.get("events", [])]
            self.assertIn("run.completed", event_types)
            self.assertIn("knowledge.extraction_triggered", event_types)
            with self.assertRaises(InvalidTerminalStateError):
                self.engine.declare_terminal(ctx, "NOT_A_TERMINAL")


if __name__ == "__main__":
    unittest.main()

