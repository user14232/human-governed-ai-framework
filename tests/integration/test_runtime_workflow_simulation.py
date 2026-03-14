from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.runtime_workflow_simulation import SimulationConfig, run_simulation


class RuntimeWorkflowSimulationIntegrationTest(unittest.TestCase):
    def test_simulation_runs_to_accepted_with_quality_checks(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            config = SimulationConfig(
                template_project_root=repo_root,
                workspace_root=workspace,
                workflow_name="default_workflow",
                target_terminal_state="ACCEPTED",
                induce_planning_block=True,
            )
            report = run_simulation(config)

            self.assertTrue(report["result"]["pass"])
            self.assertEqual(report["result"]["terminal_state"], "ACCEPTED")
            self.assertGreater(report["result"]["transition_count"], 0)

            checks = {entry["id"]: entry for entry in report["checks"]}
            self.assertTrue(checks["CHK-002"]["pass"])
            self.assertTrue(checks["CHK-003"]["pass"])
            self.assertTrue(checks["CHK-004"]["pass"])
            self.assertTrue(checks["CHK-005"]["pass"])

            run_metrics_path = Path(report["simulation_contract"]["outputs"]["run_metrics_path"])
            report_path = Path(report["simulation_contract"]["outputs"]["report_path"])
            self.assertTrue(run_metrics_path.is_file())
            self.assertTrue(report_path.is_file())


if __name__ == "__main__":
    unittest.main()
