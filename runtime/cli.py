from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Protocol

from runtime.engine.gate_evaluator import GateEvaluator as DefaultGateEvaluator
from runtime.engine.run_engine import RunEngine
from runtime.engine.workflow_engine import NoEligibleTransitionsError, WorkflowEngine
from runtime.framework.schema_loader import load_all_schemas
from runtime.types.artifact import ArtifactSchema
from runtime.types.gate import CheckResult, GateResult
from runtime.types.run import RunContext
from runtime.types.workflow import Transition


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
    ) -> dict[str, str]:
        ctx = self.resume(project_root, run_id, workflow, project_inputs_root=project_inputs_root)
        wf_engine = WorkflowEngine(ctx.workflow_def)
        evaluator = self._require_evaluator()
        schemas = load_all_schemas(project_root / "artifacts" / "schemas")
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

    def _require_evaluator(self) -> GateEvaluator:
        if self._evaluator is None:
            raise RuntimeError("Gate evaluator dependency is required for check/advance commands.")
        return self._evaluator


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
        print(json.dumps(runtime_cli.advance(project_root, args.run_id, args.workflow, project_inputs_root=project_inputs_root)))
        return 0

    parser.error(f"Unsupported command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

