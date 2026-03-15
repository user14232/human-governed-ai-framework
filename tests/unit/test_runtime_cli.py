from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout

from kernel.cli import RuntimeCLI, main
from kernel.types.artifact import ArtifactSchema
from kernel.types.gate import CheckResult, GateResult
from kernel.types.workflow import Transition


@dataclass
class PassEvaluator:
    calls: int = 0

    def evaluate(  # type: ignore[override]
        self,
        transition: Transition,
        project_inputs_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        _ = (project_inputs_root, artifacts_dir, decision_log_path, schemas)
        self.calls += 1
        return GateResult(transition=transition, result=CheckResult.PASS, checks=())


class RuntimeCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_smoke_command_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "delivery_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
            # Minimal schema file to keep schema loader behavior explicit.
            (root / "artifacts" / "schemas" / "dummy.schema.yaml").write_text(
                "schema_id: dummy\nartifact_name: dummy.yaml\nowner_roles: []\nrequired_fields: []\n",
                encoding="utf-8",
            )
            change_intent = root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")
            # Prepare required inputs so INIT deterministically advances to PLANNING on resume fallback.
            for name in (
                "domain_scope.md",
                "domain_rules.md",
                "source_policy.md",
                "glossary.md",
                "architecture_contract.md",
            ):
                (root / name).write_text("ok", encoding="utf-8")

            evaluator = PassEvaluator()
            cli = RuntimeCLI(evaluator=evaluator)

            run_ctx = cli.run(root, change_intent, "delivery_workflow")
            self.assertEqual(run_ctx.current_state, "INIT")

            status = cli.status(root, run_ctx.run_id, "delivery_workflow")
            self.assertEqual(status["current_state"], "PLANNING")

            check = cli.check(root, run_ctx.run_id, "delivery_workflow")
            self.assertEqual(check["gate_result"], "pass")

            advance = cli.advance(root, run_ctx.run_id, "delivery_workflow")
            self.assertEqual(advance["result"], "transitioned")
            self.assertEqual(advance["state"], "ARCH_CHECK")
            self.assertGreaterEqual(evaluator.calls, 2)

    def test_main_check_works_without_manual_evaluator_injection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "delivery_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
            (root / "artifacts" / "schemas" / "implementation_plan.schema.yaml").write_text(
                (self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_plan.schema.yaml").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            change_intent = root / "change_intent.yaml"
            change_intent.write_text("id: CI-1\n", encoding="utf-8")

            # Prepare required inputs for gate input_presence check.
            for name in (
                "domain_scope.md",
                "domain_rules.md",
                "source_policy.md",
                "glossary.md",
                "architecture_contract.md",
            ):
                (root / name).write_text("ok", encoding="utf-8")

            cli = RuntimeCLI()
            ctx = cli.run(root, change_intent, "delivery_workflow")
            with redirect_stdout(StringIO()):
                exit_code = main(
                    [
                        "check",
                        "--project",
                        str(root),
                        "--run-id",
                        ctx.run_id,
                        "--workflow",
                        "delivery_workflow",
                    ]
                )
            self.assertEqual(exit_code, 0)


    def test_main_run_accepts_project_inputs_root_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "workflow").mkdir(parents=True, exist_ok=True)
            (root / "workflow" / "delivery_workflow.yaml").write_text(
                (self.repo_root / "framework" / "workflows" / "delivery_workflow.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            change_intent = root / "change_intent.yaml"
            change_intent.write_text("id: CI-run-flag\n", encoding="utf-8")
            inputs_dir = root / "custom_inputs"
            inputs_dir.mkdir(parents=True, exist_ok=True)

            buf = StringIO()
            with redirect_stdout(buf):
                exit_code = main(
                    [
                        "run",
                        "--project",
                        str(root),
                        "--change-intent",
                        str(change_intent),
                        "--workflow",
                        "delivery_workflow",
                        "--project-inputs-root",
                        str(inputs_dir),
                    ]
                )
            self.assertEqual(exit_code, 0)
            import json
            result = json.loads(buf.getvalue())
            self.assertIn("run_id", result)
            self.assertEqual(result["state"], "INIT")


if __name__ == "__main__":
    unittest.main()

