from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.framework.agent_loader import ParseError as AgentParseError
from runtime.framework.agent_loader import load_agent_contract, load_all_agent_contracts
from runtime.framework.schema_loader import ParseError as SchemaParseError
from runtime.framework.schema_loader import load_all_schemas, load_schema


class SchemaAndAgentLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_load_schema_yaml(self) -> None:
        schema = load_schema(
            self.repo_root / "artifacts" / "schemas" / "implementation_plan.schema.yaml"
        )
        self.assertEqual(schema.artifact_type, "implementation_plan")
        self.assertEqual(schema.file_format, "yaml")
        self.assertIn("id", schema.required_fields)

    def test_load_schema_markdown(self) -> None:
        schema = load_schema(self.repo_root / "artifacts" / "schemas" / "review_result.schema.md")
        self.assertEqual(schema.file_format, "markdown")
        self.assertIn("Summary", schema.required_sections)
        self.assertIn("outcome", schema.required_fields)

    def test_load_all_schemas(self) -> None:
        schemas = load_all_schemas(self.repo_root / "artifacts" / "schemas")
        self.assertIn("implementation_plan", schemas)
        self.assertIn("review_result", schemas)

    def test_invalid_schema_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.schema.yaml"
            bad.write_text("- not-a-mapping\n", encoding="utf-8")
            with self.assertRaises(SchemaParseError):
                load_schema(bad)

    def test_load_single_agent_contract(self) -> None:
        contract = load_agent_contract(self.repo_root / "agents" / "agent_implementer.md")
        self.assertEqual(contract.role_id, "agent_implementer")
        self.assertIn("implementation_plan.yaml", contract.input_artifacts)
        self.assertIn("implementation_summary.md", contract.output_artifacts)

    def test_load_all_agent_contracts(self) -> None:
        contracts = load_all_agent_contracts(self.repo_root / "agents")
        self.assertIn("agent_implementer", contracts)
        self.assertIn("human_decision_authority", contracts)

    def test_invalid_agent_contract_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad_agent.md"
            bad.write_text("# bad\n", encoding="utf-8")
            with self.assertRaises(AgentParseError):
                load_agent_contract(bad)


if __name__ == "__main__":
    unittest.main()

