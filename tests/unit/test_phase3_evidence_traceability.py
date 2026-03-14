from __future__ import annotations

import re
import unittest
from pathlib import Path


class Phase3EvidenceTraceabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.record_path = self.repo_root / "docs" / "phase3_implementation_record.md"

    def test_sc_matrix_paths_exist_and_status_is_explicit(self) -> None:
        text = self.record_path.read_text(encoding="utf-8")
        rows = self._matrix_rows(text)
        self.assertEqual(len(rows), 10)

        for row in rows:
            criterion = row[0]
            claim_status = row[1]
            evidence = row[2]
            execution_tests = row[3]
            self.assertRegex(criterion, r"^SC-\d{2}\b")
            self.assertIn(claim_status, {"Verified", "Partial"})

            # Any verified SC must point to deterministic test surfaces.
            if claim_status == "Verified":
                self.assertIn("tests/", execution_tests)

            for path_text in self._extract_repo_paths(evidence + " " + execution_tests):
                self.assertTrue((self.repo_root / path_text).is_file(), f"Missing referenced file: {path_text}")

    def test_critical_sc_rows_reference_runtime_compliance_tests(self) -> None:
        text = self.record_path.read_text(encoding="utf-8")
        by_sc = {row[0].split()[0]: row for row in self._matrix_rows(text)}

        sc06 = by_sc["SC-06"]
        sc07 = by_sc["SC-07"]
        sc08 = by_sc["SC-08"]

        self.assertIn("tests/integration/test_runtime_required_events.py", sc06[3])
        self.assertIn("tests/unit/test_workflow_engine.py", sc07[3])
        self.assertEqual(sc08[1], "Verified")
        self.assertIn("tests/integration/test_secondary_workflows_e2e.py", sc08[3])

    @staticmethod
    def _matrix_rows(text: str) -> list[list[str]]:
        in_matrix = False
        rows: list[list[str]] = []
        for line in text.splitlines():
            if line.strip() == "## Success Criteria Evidence Matrix":
                in_matrix = True
                continue
            if not in_matrix:
                continue
            if line.startswith("## "):
                break
            if not line.startswith("| SC-"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            rows.append(cells)
        return rows

    @staticmethod
    def _extract_repo_paths(text: str) -> list[str]:
        candidates = re.findall(r"`([^`]+)`", text)
        result: list[str] = []
        for candidate in candidates:
            normalized = candidate.strip().replace("\\", "/")
            if "/" not in normalized:
                continue
            if not re.search(r"\.(py|md|ya?ml|json)$", normalized):
                continue
            result.append(normalized)
        return result


if __name__ == "__main__":
    unittest.main()
