from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.framework.workflow_loader import ParseError, load_workflow


class WorkflowLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_load_default_workflow(self) -> None:
        workflow = load_workflow(self.repo_root / "workflow" / "default_workflow.yaml")
        self.assertEqual(workflow.workflow_id, "default_workflow")
        self.assertGreater(len(workflow.states), 0)
        self.assertGreater(len(workflow.transitions), 0)

    def test_invalid_workflow_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "broken_workflow.yaml"
            path.write_text("id: only_id\nversion: v1\n", encoding="utf-8")
            with self.assertRaises(ParseError):
                load_workflow(path)


if __name__ == "__main__":
    unittest.main()

