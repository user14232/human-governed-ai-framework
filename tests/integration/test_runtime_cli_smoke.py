from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from runtime.cli import main


class RuntimeCliIntegrationSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_cli_run_status_check_advance_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._prepare_project(root)

            # run
            out = StringIO()
            with redirect_stdout(out):
                run_exit = main(
                    [
                        "run",
                        "--project",
                        str(root),
                        "--change-intent",
                        str(root / "change_intent.yaml"),
                        "--workflow",
                        "default_workflow",
                    ]
                )
            self.assertEqual(run_exit, 0)
            run_payload = json.loads(out.getvalue())
            run_id = run_payload["run_id"]
            self.assertEqual(run_payload["state"], "INIT")

            # status
            out = StringIO()
            with redirect_stdout(out):
                status_exit = main(
                    [
                        "status",
                        "--project",
                        str(root),
                        "--run-id",
                        run_id,
                        "--workflow",
                        "default_workflow",
                    ]
                )
            self.assertEqual(status_exit, 0)
            status_payload = json.loads(out.getvalue())
            self.assertEqual(status_payload["run_id"], run_id)

            # check
            out = StringIO()
            with redirect_stdout(out):
                check_exit = main(
                    [
                        "check",
                        "--project",
                        str(root),
                        "--run-id",
                        run_id,
                        "--workflow",
                        "default_workflow",
                    ]
                )
            self.assertEqual(check_exit, 0)
            check_payload = json.loads(out.getvalue())
            self.assertIn(check_payload["gate_result"], {"pass", "fail"})

            # advance
            out = StringIO()
            with redirect_stdout(out):
                advance_exit = main(
                    [
                        "advance",
                        "--project",
                        str(root),
                        "--run-id",
                        run_id,
                        "--workflow",
                        "default_workflow",
                    ]
                )
            self.assertEqual(advance_exit, 0)
            advance_payload = json.loads(out.getvalue())
            self.assertEqual(advance_payload["run_id"], run_id)
            self.assertIn(advance_payload["result"], {"transitioned", "blocked"})

    def _prepare_project(self, root: Path) -> None:
        (root / "workflow").mkdir(parents=True, exist_ok=True)
        (root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
        (root / "workflow" / "default_workflow.yaml").write_text(
            (self.repo_root / "framework" / "workflows" / "default_workflow.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "artifacts" / "schemas" / "implementation_plan.schema.yaml").write_text(
            (self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_plan.schema.yaml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        (root / "change_intent.yaml").write_text("id: CI-1\n", encoding="utf-8")
        # Required project inputs for gate input_presence check.
        for name in (
            "domain_scope.md",
            "domain_rules.md",
            "source_policy.md",
            "glossary.md",
            "architecture_contract.md",
        ):
            (root / name).write_text("ok\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

