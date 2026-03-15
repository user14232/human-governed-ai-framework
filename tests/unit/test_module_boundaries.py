from __future__ import annotations

import re
import unittest
from pathlib import Path


class ModuleBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_runtime_skeleton_contains_expected_core_paths(self) -> None:
        expected_paths = [
            "kernel/types/run.py",
            "kernel/types/workflow.py",
            "kernel/types/artifact.py",
            "kernel/types/event.py",
            "kernel/types/decision.py",
            "kernel/types/gate.py",
            "kernel/framework/workflow_loader.py",
            "kernel/framework/schema_loader.py",
            "kernel/framework/agent_loader.py",
            "kernel/store/run_store.py",
            "kernel/store/file_store.py",
            "kernel/engine/run_engine.py",
            "kernel/engine/workflow_engine.py",
            "kernel/engine/gate_evaluator.py",
            "kernel/cli.py",
        ]
        for relative in expected_paths:
            self.assertTrue((self.repo_root / relative).is_file(), f"Missing expected path: {relative}")

    def test_types_layer_does_not_import_runtime_execution_layers(self) -> None:
        forbidden = re.compile(r"\b(from|import)\s+kernel\.(engine|artifacts|events|decisions|agents|knowledge|cli)\b")
        for path in sorted((self.repo_root / "kernel" / "types").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(forbidden.search(text), f"types boundary violated in {path.name}")

    def test_framework_and_store_layers_do_not_import_runtime_execution_layers(self) -> None:
        forbidden = re.compile(r"\b(from|import)\s+kernel\.(engine|artifacts|events|decisions|agents|knowledge|cli)\b")
        for layer in ("framework", "store"):
            for path in sorted((self.repo_root / "kernel" / layer).glob("*.py")):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(forbidden.search(text), f"{layer} boundary violated in {path.name}")


if __name__ == "__main__":
    unittest.main()

