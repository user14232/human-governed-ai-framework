from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kernel.framework.agent_loader import ParseError as AgentParseError
from kernel.framework.agent_loader import load_agent_contract, load_all_agent_contracts
from kernel.framework.schema_loader import ParseError as SchemaParseError
from kernel.framework.schema_loader import load_all_schemas, load_schema


class SchemaAndAgentLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_load_schema_yaml(self) -> None:
        schema = load_schema(
            self.repo_root / "framework" / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
        )
        self.assertEqual(schema.artifact_type, "implementation_plan")
        self.assertEqual(schema.file_format, "yaml")
        self.assertIn("id", schema.required_fields)

    def test_load_schema_markdown(self) -> None:
        schema = load_schema(self.repo_root / "framework" / "artifacts" / "schemas" / "review_result.schema.md")
        self.assertEqual(schema.file_format, "markdown")
        self.assertIn("Summary", schema.required_sections)
        self.assertIn("outcome", schema.required_fields)

    def test_load_all_schemas(self) -> None:
        schemas = load_all_schemas(self.repo_root / "framework" / "artifacts" / "schemas")
        self.assertIn("implementation_plan", schemas)
        self.assertIn("review_result", schemas)

    def test_invalid_schema_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.schema.yaml"
            bad.write_text("- not-a-mapping\n", encoding="utf-8")
            with self.assertRaises(SchemaParseError):
                load_schema(bad)

    def test_load_single_agent_contract(self) -> None:
        contract = load_agent_contract(self.repo_root / "framework" / "agents" / "implementer.md")
        self.assertEqual(contract.role_id, "implementer")
        self.assertIn("implementation_plan.yaml", contract.input_artifacts)
        self.assertIn("implementation_summary.md", contract.output_artifacts)

    def test_load_all_agent_contracts(self) -> None:
        contracts = load_all_agent_contracts(self.repo_root / "framework" / "agents")
        self.assertIn("implementer", contracts)
        self.assertIn("reviewer", contracts)

    def test_invalid_agent_contract_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad_agent.md"
            bad.write_text("# bad\n", encoding="utf-8")
            with self.assertRaises(AgentParseError):
                load_agent_contract(bad)


if __name__ == "__main__":
    unittest.main()

