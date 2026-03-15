from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Protocol

from agent_runtime.invocation_layer import AgentInvocationLayer, InvocationMode
from kernel.engine.gate_evaluator import GateEvaluator as DefaultGateEvaluator
from kernel.engine.run_engine import RunEngine
from kernel.engine.workflow_engine import NoEligibleTransitionsError, WorkflowEngine
from kernel.framework.agent_loader import AgentContract, load_all_agent_contracts
from kernel.framework.schema_loader import load_all_schemas
from kernel.types.artifact import ArtifactSchema
from kernel.types.gate import CheckResult, GateResult
from kernel.types.run import RunContext
from kernel.types.workflow import Transition


# Default framework agents directory, resolved relative to this file at:
# <devos_repo_root>/framework/agents
_DEVOS_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_AGENTS_DIR = _DEVOS_ROOT / "framework" / "agents"


class GateEvaluator(Protocol):
    def evaluate(
        self,
        transition: Transition,
        project_inputs_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        """Evaluate one transition gate."""


class RuntimeCLI:
    """
    Explicit command orchestrator for runtime lifecycle operations.

    No hidden state is retained between commands.
    """

    def __init__(self, run_engine: RunEngine | None = None, evaluator: GateEvaluator | None = None) -> None:
        self._run_engine = run_engine or RunEngine()
        self._evaluator = evaluator or DefaultGateEvaluator()

    def run(
        self,
        project_root: Path,
        change_intent: Path,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
    ) -> RunContext:
        return self._run_engine.initialize_run(
            project_root,
            change_intent,
            workflow_name=workflow,
            project_inputs_root=project_inputs_root,
        )

    def resume(
        self,
        project_root: Path,
        run_id: str,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
    ) -> RunContext:
        return self._run_engine.resume_run(
            project_root,
            run_id,
            workflow_name=workflow,
            project_inputs_root=project_inputs_root,
        )

    def status(
        self,
        project_root: Path,
        run_id: str,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
    ) -> dict[str, str]:
        ctx = self.resume(project_root, run_id, workflow, project_inputs_root=project_inputs_root)
        return {"run_id": ctx.run_id, "current_state": ctx.current_state}

    def check(
        self,
        project_root: Path,
        run_id: str,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
    ) -> dict[str, str]:
        ctx = self.resume(project_root, run_id, workflow, project_inputs_root=project_inputs_root)
        wf_engine = WorkflowEngine(ctx.workflow_def)
        eligible = wf_engine.get_eligible_transitions(ctx.current_state)
        if not eligible:
            raise NoEligibleTransitionsError(f"No transitions from state '{ctx.current_state}'.")
        evaluator = self._require_evaluator()
        schemas = load_all_schemas(project_root / "artifacts" / "schemas")
        decision_log = ctx.run_dir / "decision_log.yaml"
        gate = evaluator.evaluate(
            transition=eligible[0],
            project_inputs_root=ctx.project_inputs_root or ctx.project_root,
            artifacts_dir=ctx.artifacts_dir,
            decision_log_path=decision_log,
            schemas=schemas,
        )
        return {
            "run_id": ctx.run_id,
            "from_state": ctx.current_state,
            "to_state": eligible[0].to_state,
            "gate_result": gate.result.value,
        }

    def advance(
        self,
        project_root: Path,
        run_id: str,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
        mode: InvocationMode = InvocationMode.HUMAN_AS_AGENT,
        agents_dir: Path | None = None,
    ) -> dict[str, str]:
        ctx = self.resume(project_root, run_id, workflow, project_inputs_root=project_inputs_root)
        schemas = load_all_schemas(project_root / "artifacts" / "schemas")

        if mode == InvocationMode.AUTOMATED:
            invocation_result = self._invoke_agent_for_state(
                ctx=ctx,
                schemas=schemas,
                agents_dir=agents_dir or _DEFAULT_AGENTS_DIR,
                mode=mode,
            )
            if invocation_result is not None:
                ctx = self.resume(
                    project_root,
                    run_id,
                    workflow,
                    project_inputs_root=project_inputs_root,
                )

        wf_engine = WorkflowEngine(ctx.workflow_def)
        evaluator = self._require_evaluator()
        decision_log = ctx.run_dir / "decision_log.yaml"
        result = wf_engine.advance(
            ctx=ctx,
            evaluator=evaluator,
            decision_log_path=decision_log,
            schemas=schemas,
        )
        if result.transitioned:
            return {"run_id": ctx.run_id, "state": result.new_state or ctx.current_state, "result": "transitioned"}
        return {"run_id": ctx.run_id, "state": ctx.current_state, "result": "blocked"}

    def invoke_agent(
        self,
        project_root: Path,
        run_id: str,
        workflow: str = "default_workflow",
        project_inputs_root: Path | None = None,
        mode: InvocationMode = InvocationMode.AUTOMATED,
        agent_role: str | None = None,
        agents_dir: Path | None = None,
    ) -> dict[str, object]:
        """
        Invoke the agent for the current workflow state.

        In AUTOMATED mode, the LLMAgentAdapter is created from environment configuration
        (DEVOS_LLM_API_URL, DEVOS_LLM_API_KEY, and optionally DEVOS_LLM_MODEL).

        In HUMAN_AS_AGENT mode, the runtime expects artifacts to already be written
        to the run artifacts directory by the operator.

        Args:
            project_root:        Workspace root containing workflow/ and artifacts/schemas/.
            run_id:              Run identifier (e.g. RUN-20260315-0001).
            workflow:            Workflow name (default: default_workflow).
            project_inputs_root: Optional override for project input files root.
            mode:                AUTOMATED (default) or HUMAN_AS_AGENT.
            agent_role:          Explicit agent role to invoke. Auto-detected from current
                                 workflow state if not provided.
            agents_dir:          Directory containing agent contract .md files. Defaults to
                                 <devos_repo>/framework/agents.

        Returns:
            Dict with keys: run_id, agent_role, outcome, output_artifacts, state.
        """
        ctx = self.resume(project_root, run_id, workflow, project_inputs_root=project_inputs_root)
        schemas = load_all_schemas(project_root / "artifacts" / "schemas")
        resolved_agents_dir = agents_dir or _DEFAULT_AGENTS_DIR
        contracts = _load_contracts(resolved_agents_dir)

        resolved_role = agent_role or _agent_role_for_state(contracts, ctx.current_state)
        if resolved_role is None:
            return {
                "run_id": ctx.run_id,
                "state": ctx.current_state,
                "agent_role": None,
                "outcome": "no_agent",
                "detail": f"No agent contract found for workflow state '{ctx.current_state}'.",
            }

        contract = contracts.get(resolved_role)
        if contract is None:
            raise ValueError(f"Agent role '{resolved_role}' not found in contracts at {resolved_agents_dir}.")

        layer = AgentInvocationLayer()
        result = layer.invoke(
            ctx=ctx,
            agent_role=resolved_role,
            agent_contracts=contracts,
            schemas=schemas,
            mode=mode,
            adapter=None,
        )

        return {
            "run_id": ctx.run_id,
            "state": ctx.current_state,
            "agent_role": resolved_role,
            "outcome": result.outcome.value,
            "output_artifacts": [ref.name for ref in result.output_refs],
        }

    def _invoke_agent_for_state(
        self,
        ctx: RunContext,
        schemas: dict[str, ArtifactSchema],
        agents_dir: Path,
        mode: InvocationMode,
    ) -> dict[str, object] | None:
        """
        Invoke the agent for the current workflow state if one exists and artifacts
        are not already present.

        Returns the invocation result dict if an agent was invoked, None otherwise.
        """
        contracts = _load_contracts(agents_dir)
        agent_role = _agent_role_for_state(contracts, ctx.current_state)
        if agent_role is None:
            return None

        contract = contracts[agent_role]
        if _output_artifacts_present(ctx, contract):
            return None

        layer = AgentInvocationLayer()
        result = layer.invoke(
            ctx=ctx,
            agent_role=agent_role,
            agent_contracts=contracts,
            schemas=schemas,
            mode=mode,
            adapter=None,
        )
        return {
            "agent_role": agent_role,
            "outcome": result.outcome.value,
            "output_artifacts": [ref.name for ref in result.output_refs],
        }

    def _require_evaluator(self) -> GateEvaluator:
        if self._evaluator is None:
            raise RuntimeError("Gate evaluator dependency is required for check/advance commands.")
        return self._evaluator


def _load_contracts(agents_dir: Path) -> dict[str, AgentContract]:
    """Load all agent contracts. Returns empty dict if directory does not exist."""
    if not agents_dir.is_dir():
        return {}
    return load_all_agent_contracts(agents_dir)


def _agent_role_for_state(
    contracts: dict[str, AgentContract],
    current_state: str,
) -> str | None:
    """
    Return the role_id of the agent whose workflow_states includes current_state.

    Deterministic: iterates contracts in sorted key order. Returns the first match.
    Returns None if no agent is mapped to the current state.
    """
    for role_id in sorted(contracts.keys()):
        contract = contracts[role_id]
        if current_state in contract.workflow_states:
            return role_id
    return None


def _output_artifacts_present(ctx: RunContext, contract: AgentContract) -> bool:
    """
    Return True iff ALL declared output artifacts of the contract already exist
    in the run artifacts directory.
    """
    return all((ctx.artifacts_dir / name).is_file() for name in contract.output_artifacts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devos-runtime", description="Deterministic runtime CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--project", required=True)
    run_p.add_argument("--change-intent", required=True)
    run_p.add_argument("--workflow", default="default_workflow")
    run_p.add_argument("--project-inputs-root", default=None)

    resume_p = sub.add_parser("resume")
    resume_p.add_argument("--project", required=True)
    resume_p.add_argument("--run-id", required=True)
    resume_p.add_argument("--workflow", default="default_workflow")
    resume_p.add_argument("--project-inputs-root", default=None)

    status_p = sub.add_parser("status")
    status_p.add_argument("--project", required=True)
    status_p.add_argument("--run-id", required=True)
    status_p.add_argument("--workflow", default="default_workflow")
    status_p.add_argument("--project-inputs-root", default=None)

    check_p = sub.add_parser("check")
    check_p.add_argument("--project", required=True)
    check_p.add_argument("--run-id", required=True)
    check_p.add_argument("--workflow", default="default_workflow")
    check_p.add_argument("--project-inputs-root", default=None)

    advance_p = sub.add_parser("advance")
    advance_p.add_argument("--project", required=True)
    advance_p.add_argument("--run-id", required=True)
    advance_p.add_argument("--workflow", default="default_workflow")
    advance_p.add_argument("--project-inputs-root", default=None)
    advance_p.add_argument(
        "--mode",
        choices=["automated", "manual"],
        default="manual",
        help=(
            "Agent invocation mode. "
            "'automated' invokes the LLM adapter before advancing. "
            "'manual' (default) expects artifacts to be present already."
        ),
    )
    advance_p.add_argument(
        "--agents-dir",
        default=None,
        help="Path to directory containing agent contract .md files.",
    )

    invoke_p = sub.add_parser("invoke")
    invoke_p.add_argument("--project", required=True)
    invoke_p.add_argument("--run-id", required=True)
    invoke_p.add_argument("--workflow", default="default_workflow")
    invoke_p.add_argument("--project-inputs-root", default=None)
    invoke_p.add_argument(
        "--mode",
        choices=["automated", "manual"],
        default="automated",
        help=(
            "Agent invocation mode. "
            "'automated' (default) uses the LLM adapter. "
            "'manual' expects artifacts to be written by the operator."
        ),
    )
    invoke_p.add_argument(
        "--agent",
        default=None,
        dest="agent_role",
        help="Explicit agent role to invoke. Auto-detected from current state if omitted.",
    )
    invoke_p.add_argument(
        "--agents-dir",
        default=None,
        help="Path to directory containing agent contract .md files.",
    )

    return parser


def main(argv: list[str] | None = None, cli: RuntimeCLI | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime_cli = cli or RuntimeCLI()

    project_root = Path(args.project).resolve()
    raw_inputs_root = getattr(args, "project_inputs_root", None)
    project_inputs_root = Path(raw_inputs_root).resolve() if raw_inputs_root else None
    command = args.command

    if command == "run":
        ctx = runtime_cli.run(
            project_root,
            Path(args.change_intent).resolve(),
            args.workflow,
            project_inputs_root=project_inputs_root,
        )
        print(json.dumps({"run_id": ctx.run_id, "state": ctx.current_state}))
        return 0

    if command == "resume":
        ctx = runtime_cli.resume(project_root, args.run_id, args.workflow, project_inputs_root=project_inputs_root)
        print(json.dumps({"run_id": ctx.run_id, "state": ctx.current_state}))
        return 0

    if command == "status":
        print(json.dumps(runtime_cli.status(project_root, args.run_id, args.workflow, project_inputs_root=project_inputs_root)))
        return 0

    if command == "check":
        print(json.dumps(runtime_cli.check(project_root, args.run_id, args.workflow, project_inputs_root=project_inputs_root)))
        return 0

    if command == "advance":
        mode = InvocationMode.AUTOMATED if args.mode == "automated" else InvocationMode.HUMAN_AS_AGENT
        raw_agents_dir = getattr(args, "agents_dir", None)
        agents_dir = Path(raw_agents_dir).resolve() if raw_agents_dir else None
        print(json.dumps(runtime_cli.advance(
            project_root,
            args.run_id,
            args.workflow,
            project_inputs_root=project_inputs_root,
            mode=mode,
            agents_dir=agents_dir,
        )))
        return 0

    if command == "invoke":
        mode = InvocationMode.AUTOMATED if args.mode == "automated" else InvocationMode.HUMAN_AS_AGENT
        raw_agents_dir = getattr(args, "agents_dir", None)
        agents_dir = Path(raw_agents_dir).resolve() if raw_agents_dir else None
        print(json.dumps(runtime_cli.invoke_agent(
            project_root=project_root,
            run_id=args.run_id,
            workflow=args.workflow,
            project_inputs_root=project_inputs_root,
            mode=mode,
            agent_role=getattr(args, "agent_role", None),
            agents_dir=agents_dir,
        )))
        return 0

    parser.error(f"Unsupported command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
