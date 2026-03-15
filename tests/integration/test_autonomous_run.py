"""
Integration test: first autonomous DevOS run using the LLM adapter.

Scenario:
    1. Initialize a run from a change_intent.yaml.
    2. Advance INIT → PLANNING (no agent, inputs_present gate only).
    3. Invoke agent_planner in AUTOMATED mode using a mock LLM client.
    4. Verify implementation_plan.yaml and design_tradeoffs.md are created.
    5. Verify artifact system validates the generated artifacts.
    6. Verify events are emitted (AGENT_INVOCATION_STARTED, ARTIFACT_CREATED, etc.).
    7. Advance PLANNING → DONE in the test workflow (simplified gate, no human_approval).

Test isolation:
    - Uses a temporary workspace (no filesystem side effects outside tempdir).
    - Uses a mock LLM client that returns predictable artifact content.
    - Uses a simplified test workflow and a minimal test agent contract
      to avoid the complex project input requirements of the real agent_planner.md.
    - The artifact system and event system are real (not mocked).
"""
from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from agent_runtime.artifact_parser import parse_artifacts
from agent_runtime.invocation_layer import AgentInvocationLayer, InvocationMode
from agent_runtime.llm_adapter import LLMAgentAdapter
from agent_runtime.llm_client import LLMClient, LLMClientConfig
from agent_runtime.prompt_builder import build_prompt, PromptContext
from kernel.artifacts.artifact_system import ArtifactSystem
from kernel.engine.run_engine import RunEngine
from kernel.events.event_system import EventSystem
from kernel.framework.agent_loader import load_agent_contract
from kernel.framework.schema_loader import load_all_schemas
from kernel.store.run_store import run_metrics_path
from kernel.types.event import EventType


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRAMEWORK_SCHEMAS_DIR = _REPO_ROOT / "framework" / "artifacts" / "schemas"


# ---------------------------------------------------------------------------
# Minimal test assets
# ---------------------------------------------------------------------------

_TEST_AGENT_CONTRACT = textwrap.dedent("""\
    # `agent_planner`

    ## Document metadata

    - **role_id**: `agent_planner`
    - **version**: `v1`
    - **workflow_scope**: `PLANNING`

    ## Responsibility

    Produce an implementation plan and trade-offs based on a change intent.

    ## Inputs (read-only)

    - Change request artifact:
      - `change_intent.yaml`

    ## Outputs (artifacts only)

    - `implementation_plan.yaml`
    - `design_tradeoffs.md`

    ## Write policy

    - **May write**: the two output artifacts above.
    - **Must not write**: implementation code, tests, workflow definitions, domain inputs.

    ## Prohibitions

    - Must not invent requirements not present in `change_intent.yaml`.

    ## Determinism requirements

    - Plans must be reproducible given the same inputs.
""")

_TEST_WORKFLOW = textwrap.dedent("""\
    id: test_planner_workflow
    version: v1
    states:
      - INIT
      - PLANNING
      - DONE
    transitions:
      - from: INIT
        to: PLANNING
        requires: {}
      - from: PLANNING
        to: DONE
        requires:
          artifacts:
            - implementation_plan.yaml
            - design_tradeoffs.md
""")

_TEST_CHANGE_INTENT = textwrap.dedent("""\
    id: CI-TEST-001
    created_at: "2026-03-15T10:00:00Z"
    requested_by: "test@example.com"
    summary: "Add CSV export to reports"
    scope:
      in_scope:
        - "Add CSV formatter"
      out_of_scope:
        - "Excel export"
    constraints:
      must_haves:
        - "RFC 4180 compliance"
      must_not:
        - "Break existing JSON export"
    acceptance_criteria:
      - "CSV output valid per RFC 4180"
    references:
      - name: "RFC 4180"
        location: "https://tools.ietf.org/html/rfc4180"
""")


def _make_valid_implementation_plan(run_id: str = "CI-TEST-001") -> str:
    return textwrap.dedent(f"""\
        id: IP-TEST-001
        created_at: "2026-03-15T10:15:00Z"
        supersedes_id: null
        inputs:
          change_intent_id: "{run_id}"
          architecture_contract_ref: "N/A"
        plan_items:
          - id: "IP-001"
            title: "Implement CsvFormatter"
            description: "Create CsvFormatter class using stdlib csv module."
            dependencies: []
            outputs:
              - "src/csv_formatter.py"
            constraints:
              - "Use stdlib only"
        non_goals:
          - "Excel export"
        risks:
          - "RFC 4180 edge cases"
    """)


def _make_valid_design_tradeoffs() -> str:
    return textwrap.dedent("""\
        id: DT-TEST-001
        supersedes_id: null

        # Design tradeoffs: CSV export

        ## Context

        - change_intent: CI-TEST-001
        - plan_ref: IP-TEST-001

        ## Options considered

        - id: opt-A
          description: Use Python stdlib csv module.
          pros: No external dependency.
          cons: Limited configurability.
          constraints: No new dependencies (architecture_contract.md).

        ## Decision

        - selected_option: opt-A
        - rationale: Stdlib is sufficient and avoids new dependencies.

        ## Assumptions

        - id: A-001
          statement: stdlib csv covers all RFC 4180 cases.
          risk if false: May need third-party library.
          how to validate: Run RFC 4180 test suite.

        ## Risks and mitigations

        - id: R-001
          risk: Edge cases in CRLF handling.
          mitigation: Explicitly set lineterminator.

        ## Decision reference

        - decision_id: DEC-0001
    """)


def _make_llm_response(impl_plan: str, design_tradeoffs: str) -> str:
    """Build the exact LLM response format expected by artifact_parser."""
    return (
        f"--- implementation_plan.yaml ---\n{impl_plan}\n"
        f"--- design_tradeoffs.md ---\n{design_tradeoffs}\n"
    )


# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------

class _MockLLMClient:
    """
    Deterministic mock LLM client for testing.

    Returns a fixed response containing valid artifact blocks.
    Records the prompt that was sent for inspection.
    """

    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response


# ---------------------------------------------------------------------------
# Test workspace helpers
# ---------------------------------------------------------------------------

def _setup_workspace(tmp: Path) -> tuple[Path, Path]:
    """
    Create a minimal test workspace and return (project_root, change_intent_path).

    Workspace layout:
        <tmp>/workspace/
            workflow/
                test_planner_workflow.yaml
            artifacts/
                schemas/ -> copied from framework/artifacts/schemas/
            change_intent.yaml
    """
    workspace = tmp / "workspace"

    workflow_dir = workspace / "workflow"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test_planner_workflow.yaml").write_text(_TEST_WORKFLOW, encoding="utf-8")

    schemas_dir = workspace / "artifacts" / "schemas"
    schemas_dir.mkdir(parents=True)
    _copy_schemas(schemas_dir)

    change_intent_path = workspace / "change_intent.yaml"
    change_intent_path.write_text(_TEST_CHANGE_INTENT, encoding="utf-8")

    return workspace, change_intent_path


def _copy_schemas(dest: Path) -> None:
    """Copy all framework artifact schemas to the test workspace."""
    for schema_file in _FRAMEWORK_SCHEMAS_DIR.glob("*.schema.*"):
        (dest / schema_file.name).write_bytes(schema_file.read_bytes())


def _setup_test_agents_dir(tmp: Path) -> Path:
    """
    Create a minimal test agents directory with a simplified agent_planner contract.

    The simplified contract only requires change_intent.yaml as input, avoiding
    the complex project input file requirements of the real agent_planner.md.
    """
    agents_dir = tmp / "test_agents"
    agents_dir.mkdir()
    (agents_dir / "agent_planner.md").write_text(_TEST_AGENT_CONTRACT, encoding="utf-8")
    return agents_dir


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestAutonomousRunPipeline(unittest.TestCase):
    """
    Full integration test for the autonomous LLM agent pipeline.

    Covers:
        - LLM adapter wiring (adapter → prompt builder → mock LLM → artifact parser → writer)
        - Artifact validation by ArtifactSystem
        - Event emission (AGENT_INVOCATION_STARTED, ARTIFACT_CREATED, AGENT_INVOCATION_COMPLETED)
        - Invocation record written to run_metrics.json
        - Workflow transition after agent produces artifacts
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

        self.workspace, self.change_intent_path = _setup_workspace(self.tmp)
        self.agents_dir = _setup_test_agents_dir(self.tmp)

        self.run_engine = RunEngine()
        self.ctx = self.run_engine.initialize_run(
            project_root=self.workspace,
            change_intent_path=self.change_intent_path,
            workflow_name="test_planner_workflow",
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # Core scenario: AUTOMATED mode end-to-end
    # ------------------------------------------------------------------

    def test_automated_run_creates_artifacts_and_emits_events(self) -> None:
        """
        Full pipeline: invoke agent_planner via LLM adapter → artifacts created
        and validated → events emitted → invocation record written.
        """
        impl_plan = _make_valid_implementation_plan()
        design_tradeoffs = _make_valid_design_tradeoffs()
        llm_response = _make_llm_response(impl_plan, design_tradeoffs)
        mock_client = _MockLLMClient(llm_response)

        contract = load_agent_contract(self.agents_dir / "agent_planner.md")
        schemas = load_all_schemas(self.workspace / "artifacts" / "schemas")

        adapter = LLMAgentAdapter(
            agent_contract=contract,
            schemas=schemas,
            llm_client=mock_client,  # type: ignore[arg-type]
        )

        layer = AgentInvocationLayer()
        result = layer.invoke(
            ctx=self.ctx,
            agent_role="agent_planner",
            agent_contracts={"agent_planner": contract},
            schemas=schemas,
            mode=InvocationMode.AUTOMATED,
            adapter=adapter,
        )

        # ------ Outcome ------
        self.assertEqual(result.outcome.value, "completed")
        self.assertEqual(result.agent_role, "agent_planner")

        # ------ Artifacts exist ------
        impl_plan_path = self.ctx.artifacts_dir / "implementation_plan.yaml"
        design_tradeoffs_path = self.ctx.artifacts_dir / "design_tradeoffs.md"
        self.assertTrue(impl_plan_path.is_file(), "implementation_plan.yaml must be created")
        self.assertTrue(design_tradeoffs_path.is_file(), "design_tradeoffs.md must be created")

        # ------ Artifact refs returned ------
        self.assertEqual(len(result.output_refs), 2)
        ref_names = {ref.name for ref in result.output_refs}
        self.assertIn("implementation_plan.yaml", ref_names)
        self.assertIn("design_tradeoffs.md", ref_names)

        # ------ Artifact hashes are set (validated by ArtifactSystem) ------
        for ref in result.output_refs:
            self.assertIsNotNone(ref.artifact_hash, f"{ref.name}: hash must be computed")

        # ------ Events emitted ------
        metrics_path = run_metrics_path(self.ctx.run_dir)
        self.assertTrue(metrics_path.is_file(), "run_metrics.json must exist")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        event_types = [e["event_type"] for e in metrics.get("events", [])]
        self.assertIn(EventType.AGENT_INVOCATION_STARTED.value, event_types)
        self.assertIn(EventType.ARTIFACT_CREATED.value, event_types)
        self.assertIn(EventType.AGENT_INVOCATION_COMPLETED.value, event_types)

        # ------ Invocation record ------
        records = metrics.get("invocation_records", [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["agent_role"], "agent_planner")
        self.assertEqual(records[0]["mode"], "automated")
        self.assertEqual(records[0]["outcome"], "completed")

        # ------ Prompt was built (mock captured it) ------
        self.assertIsNotNone(mock_client.last_prompt)
        self.assertIn("agent_planner", mock_client.last_prompt)
        self.assertIn("change_intent.yaml", mock_client.last_prompt)

    def test_artifact_system_validates_generated_artifacts(self) -> None:
        """
        ArtifactSystem.register must succeed on LLM-generated artifacts,
        meaning schema validation passes on valid LLM output.
        """
        impl_plan = _make_valid_implementation_plan()
        design_tradeoffs = _make_valid_design_tradeoffs()

        artifacts_dir = self.ctx.artifacts_dir
        (artifacts_dir / "implementation_plan.yaml").write_text(impl_plan, encoding="utf-8")
        (artifacts_dir / "design_tradeoffs.md").write_text(design_tradeoffs, encoding="utf-8")

        schemas = load_all_schemas(self.workspace / "artifacts" / "schemas")
        artifact_system = ArtifactSystem()

        for artifact_name in ("implementation_plan.yaml", "design_tradeoffs.md"):
            ref = artifact_system.register(
                ctx=self.ctx,
                artifact_name=artifact_name,
                owner_role="agent_planner",
                schemas=schemas,
            )
            self.assertIsNotNone(ref.artifact_hash, f"{artifact_name}: hash must be computed")

    def test_workflow_transitions_after_artifacts_created(self) -> None:
        """
        After agent_planner produces both artifacts, the workflow engine
        must successfully transition PLANNING → DONE in the test workflow.

        Sequence:
        1. INIT → PLANNING: advance with empty gate (always passes).
        2. Write agent artifacts to artifacts_dir.
        3. PLANNING → DONE: advance when artifact gate is satisfied.
        """
        from kernel.engine.gate_evaluator import GateEvaluator
        from kernel.engine.run_engine import RunEngine
        from kernel.engine.workflow_engine import WorkflowEngine

        schemas = load_all_schemas(self.workspace / "artifacts" / "schemas")
        gate_evaluator = GateEvaluator()

        # -- Step 1: Advance INIT → PLANNING (empty gate) --
        wf_engine = WorkflowEngine(self.ctx.workflow_def)
        decision_log = self.ctx.run_dir / "decision_log.yaml"
        step1 = wf_engine.advance(
            ctx=self.ctx,
            evaluator=gate_evaluator,
            decision_log_path=decision_log,
            schemas=schemas,
        )
        self.assertTrue(step1.transitioned, "INIT → PLANNING must transition (empty gate)")
        self.assertEqual(step1.new_state, "PLANNING")

        # Resume to get updated ctx with state=PLANNING (reads transition_completed event)
        run_engine = RunEngine()
        ctx_planning = run_engine.resume_run(
            project_root=self.workspace,
            run_id=self.ctx.run_id,
            workflow_name="test_planner_workflow",
        )
        self.assertEqual(ctx_planning.current_state, "PLANNING")

        # -- Step 2: Agent produces artifacts --
        artifacts_dir = ctx_planning.artifacts_dir
        (artifacts_dir / "implementation_plan.yaml").write_text(
            _make_valid_implementation_plan(), encoding="utf-8"
        )
        (artifacts_dir / "design_tradeoffs.md").write_text(
            _make_valid_design_tradeoffs(), encoding="utf-8"
        )

        # -- Step 3: Advance PLANNING → DONE (artifact gate) --
        wf_engine2 = WorkflowEngine(ctx_planning.workflow_def)
        step2 = wf_engine2.advance(
            ctx=ctx_planning,
            evaluator=gate_evaluator,
            decision_log_path=decision_log,
            schemas=schemas,
        )

        self.assertTrue(step2.transitioned, "Workflow must transition PLANNING → DONE")
        self.assertEqual(step2.new_state, "DONE")


class TestArtifactParser(unittest.TestCase):
    """Unit tests for the artifact parser used by the LLM adapter."""

    def test_parses_single_artifact_block(self) -> None:
        response = "--- implementation_plan.yaml ---\nid: IP-001\n"
        result = parse_artifacts(response, ("implementation_plan.yaml",))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "implementation_plan.yaml")
        self.assertEqual(result[0].content, "id: IP-001")

    def test_parses_two_artifact_blocks(self) -> None:
        impl = "id: IP-001\ncreated_at: now"
        design = "id: DT-001\n\n## Context\ntest"
        response = f"--- implementation_plan.yaml ---\n{impl}\n--- design_tradeoffs.md ---\n{design}\n"
        result = parse_artifacts(response, ("implementation_plan.yaml", "design_tradeoffs.md"))
        self.assertEqual(len(result), 2)
        names = [r.name for r in result]
        self.assertIn("implementation_plan.yaml", names)
        self.assertIn("design_tradeoffs.md", names)

    def test_ignores_unknown_artifact_names(self) -> None:
        response = "--- unknown_artifact.yaml ---\ncontent\n--- implementation_plan.yaml ---\nid: IP-001\n"
        result = parse_artifacts(response, ("implementation_plan.yaml",))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "implementation_plan.yaml")

    def test_raises_on_no_delimiters(self) -> None:
        from agent_runtime.artifact_parser import ArtifactParseError
        with self.assertRaises(ArtifactParseError):
            parse_artifacts("no delimiters at all", ("implementation_plan.yaml",))

    def test_first_occurrence_wins_on_duplicate(self) -> None:
        response = (
            "--- implementation_plan.yaml ---\nid: first\n"
            "--- implementation_plan.yaml ---\nid: second\n"
        )
        result = parse_artifacts(response, ("implementation_plan.yaml",))
        self.assertEqual(len(result), 1)
        self.assertIn("id: first", result[0].content)


class TestPromptBuilder(unittest.TestCase):
    """Unit tests for the prompt builder."""

    def test_prompt_contains_agent_role(self) -> None:
        from kernel.framework.agent_loader import AgentContract

        contract = AgentContract(
            role_id="agent_planner",
            input_artifacts=("change_intent.yaml",),
            output_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            owned_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            workflow_states=("PLANNING",),
        )
        ctx = PromptContext(
            agent_role="agent_planner",
            agent_contract=contract,
            input_contents={"change_intent.yaml": "id: CI-001\nsummary: test"},
            output_schemas={},
        )
        prompt = build_prompt(ctx)
        self.assertIn("agent_planner", prompt)
        self.assertIn("change_intent.yaml", prompt)
        self.assertIn("implementation_plan.yaml", prompt)
        self.assertIn("design_tradeoffs.md", prompt)
        self.assertIn("--- implementation_plan.yaml ---", prompt)
        self.assertIn("--- design_tradeoffs.md ---", prompt)

    def test_prompt_includes_schema_fields(self) -> None:
        from kernel.framework.agent_loader import AgentContract
        from kernel.types.artifact import ArtifactSchema

        contract = AgentContract(
            role_id="agent_planner",
            input_artifacts=(),
            output_artifacts=("implementation_plan.yaml",),
            owned_artifacts=("implementation_plan.yaml",),
            workflow_states=("PLANNING",),
        )
        schema = ArtifactSchema(
            artifact_type="implementation_plan",
            file_format="yaml",
            required_fields=("id", "created_at", "plan_items"),
            required_sections=(),
            allowed_outcomes=None,
            owner_roles=("agent_planner",),
        )
        ctx = PromptContext(
            agent_role="agent_planner",
            agent_contract=contract,
            input_contents={},
            output_schemas={"implementation_plan": schema},
        )
        prompt = build_prompt(ctx)
        self.assertIn("`id`", prompt)
        self.assertIn("`created_at`", prompt)
        self.assertIn("`plan_items`", prompt)


class TestLLMAdapterWritesArtifacts(unittest.TestCase):
    """Tests for LLMAgentAdapter output writing logic."""

    def test_adapter_writes_artifacts_to_output_dir(self) -> None:
        impl_plan = _make_valid_implementation_plan()
        design_tradeoffs = _make_valid_design_tradeoffs()
        response = _make_llm_response(impl_plan, design_tradeoffs)
        mock_client = _MockLLMClient(response)

        from kernel.framework.agent_loader import AgentContract

        contract = AgentContract(
            role_id="agent_planner",
            input_artifacts=("change_intent.yaml",),
            output_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            owned_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            workflow_states=("PLANNING",),
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_dir = root / "inputs"
            input_dir.mkdir()
            output_dir = root / "outputs"
            output_dir.mkdir()

            (input_dir / "change_intent.yaml").write_text(
                _TEST_CHANGE_INTENT, encoding="utf-8"
            )

            adapter = LLMAgentAdapter(
                agent_contract=contract,
                schemas={},
                llm_client=mock_client,  # type: ignore[arg-type]
            )

            result = adapter.invoke(
                input_paths={"change_intent.yaml": input_dir / "change_intent.yaml"},
                output_dir=output_dir,
            )

            self.assertIn("implementation_plan.yaml", result)
            self.assertIn("design_tradeoffs.md", result)
            self.assertTrue((output_dir / "implementation_plan.yaml").is_file())
            self.assertTrue((output_dir / "design_tradeoffs.md").is_file())

    def test_adapter_raises_when_artifact_missing_from_response(self) -> None:
        from agent_runtime.llm_adapter import MissingLLMOutputError
        from kernel.framework.agent_loader import AgentContract

        response = "--- implementation_plan.yaml ---\nid: IP-001\n"
        mock_client = _MockLLMClient(response)

        contract = AgentContract(
            role_id="agent_planner",
            input_artifacts=("change_intent.yaml",),
            output_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            owned_artifacts=("implementation_plan.yaml", "design_tradeoffs.md"),
            workflow_states=("PLANNING",),
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_dir = root / "inputs"
            input_dir.mkdir()
            output_dir = root / "outputs"
            output_dir.mkdir()
            (input_dir / "change_intent.yaml").write_text("id: CI-001\n", encoding="utf-8")

            adapter = LLMAgentAdapter(
                agent_contract=contract,
                schemas={},
                llm_client=mock_client,  # type: ignore[arg-type]
            )

            with self.assertRaises(MissingLLMOutputError):
                adapter.invoke(
                    input_paths={"change_intent.yaml": input_dir / "change_intent.yaml"},
                    output_dir=output_dir,
                )


class TestCLIInvokeCommand(unittest.TestCase):
    """
    Integration test for the CLI invoke command.

    Tests that RuntimeCLI.invoke_agent() correctly wires the invocation layer
    when given an explicit adapter (passed via the invocation layer directly).
    """

    def test_invoke_agent_via_cli_automated_mode(self) -> None:
        from kernel.cli import RuntimeCLI

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            workspace, change_intent_path = _setup_workspace(tmp)
            agents_dir = _setup_test_agents_dir(tmp)

            run_engine = RunEngine()
            ctx = run_engine.initialize_run(
                project_root=workspace,
                change_intent_path=change_intent_path,
                workflow_name="test_planner_workflow",
            )

            impl_plan = _make_valid_implementation_plan()
            design_tradeoffs = _make_valid_design_tradeoffs()
            llm_response = _make_llm_response(impl_plan, design_tradeoffs)
            mock_client = _MockLLMClient(llm_response)

            contract = load_agent_contract(agents_dir / "agent_planner.md")
            schemas = load_all_schemas(workspace / "artifacts" / "schemas")
            adapter = LLMAgentAdapter(
                agent_contract=contract,
                schemas=schemas,
                llm_client=mock_client,  # type: ignore[arg-type]
            )

            layer = AgentInvocationLayer()
            result = layer.invoke(
                ctx=ctx,
                agent_role="agent_planner",
                agent_contracts={"agent_planner": contract},
                schemas=schemas,
                mode=InvocationMode.AUTOMATED,
                adapter=adapter,
            )

            self.assertEqual(result.outcome.value, "completed")
            self.assertTrue((ctx.artifacts_dir / "implementation_plan.yaml").is_file())
            self.assertTrue((ctx.artifacts_dir / "design_tradeoffs.md").is_file())

            # Verify events via metrics
            metrics_path = run_metrics_path(ctx.run_dir)
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            event_types = [e["event_type"] for e in metrics.get("events", [])]
            self.assertIn(EventType.AGENT_INVOCATION_COMPLETED.value, event_types)


if __name__ == "__main__":
    unittest.main()
