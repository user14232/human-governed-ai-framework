from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.agents.invocation_layer import AgentInvocationLayer, InvocationMode
from runtime.decisions.decision_system import DecisionSystem
from runtime.engine.gate_evaluator import GateEvaluator
from runtime.engine.run_engine import RunEngine
from runtime.engine.workflow_engine import AdvanceResult, WorkflowEngine
from runtime.events.event_system import EventSystem
from runtime.framework.agent_loader import AgentContract
from runtime.framework.schema_loader import load_all_schemas
from runtime.types.artifact import ArtifactRef, ArtifactSchema
from runtime.types.run import RunContext, TERMINAL_STATES


FIXED_ARTIFACT_CREATED_AT = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class SimulationConfig:
    template_project_root: Path
    workspace_root: Path
    workflow_name: str
    target_terminal_state: str
    induce_planning_block: bool


def run_simulation(config: SimulationConfig) -> dict[str, Any]:
    if config.target_terminal_state not in {"ACCEPTED", "ACCEPTED_WITH_DEBT", "FAILED"}:
        raise ValueError("target_terminal_state must be one of: ACCEPTED, ACCEPTED_WITH_DEBT, FAILED.")

    _prepare_workspace(
        template_project_root=config.template_project_root,
        workspace_root=config.workspace_root,
        workflow_name=config.workflow_name,
    )

    events = EventSystem()
    run_engine = RunEngine(event_system=events)
    evaluator = GateEvaluator()
    invocation_layer = AgentInvocationLayer(event_system=events)
    decision_system = DecisionSystem(event_system=events)

    change_intent_path = config.workspace_root / "change_intent.yaml"
    ctx = run_engine.initialize_run(
        project_root=config.workspace_root,
        change_intent_path=change_intent_path,
        workflow_name=config.workflow_name,
    )
    schemas = load_all_schemas(config.workspace_root / "artifacts" / "schemas")

    decisions: list[dict[str, Any]] = []
    known_decision_count = 0
    transition_trace: list[dict[str, str]] = []
    blocked_trace: list[dict[str, str]] = []
    planning_block_checked = False

    hop_limit = max(len(ctx.workflow_def.transitions) * 3, 10)
    hops = 0
    while ctx.current_state not in TERMINAL_STATES and hops < hop_limit:
        hops += 1

        if config.induce_planning_block and ctx.current_state == "PLANNING" and not planning_block_checked:
            blocked = _advance_once(ctx=ctx, evaluator=evaluator, schemas=schemas)
            if blocked.transitioned:
                raise RuntimeError("Expected PLANNING blocker did not occur.")
            blocked_trace.append(
                {
                    "state": ctx.current_state,
                    "reason": "planning_gate_without_artifacts",
                }
            )
            planning_block_checked = True

        known_decision_count = _materialize_state_artifacts(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            decision_system=decision_system,
            decisions=decisions,
            known_decision_count=known_decision_count,
            target_terminal_state=config.target_terminal_state,
        )

        advanced = _advance_once(ctx=ctx, evaluator=evaluator, schemas=schemas)
        if not advanced.transitioned or not advanced.new_state:
            raise RuntimeError(f"Unexpected block at state '{ctx.current_state}'.")
        transition_trace.append({"from": ctx.current_state, "to": advanced.new_state})
        ctx = replace(ctx, current_state=advanced.new_state)

    if ctx.current_state != config.target_terminal_state:
        raise RuntimeError(
            f"Simulation terminated in '{ctx.current_state}', expected '{config.target_terminal_state}'."
        )

    run_engine.declare_terminal(ctx, ctx.current_state)
    metrics_path = ctx.artifacts_dir / "run_metrics.json"
    metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    report = _build_quality_report(
        ctx=ctx,
        metrics_payload=metrics_payload,
        target_terminal_state=config.target_terminal_state,
        transition_trace=transition_trace,
        blocked_trace=blocked_trace,
        induce_planning_block=config.induce_planning_block,
        decision_count=len(decisions),
    )

    report_path = ctx.artifacts_dir / "simulation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _prepare_workspace(template_project_root: Path, workspace_root: Path, workflow_name: str) -> None:
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    (workspace_root / "workflow").mkdir(parents=True, exist_ok=True)
    (workspace_root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)

    workflow_src = template_project_root / "workflow" / f"{workflow_name}.yaml"
    workflow_dst = workspace_root / "workflow" / f"{workflow_name}.yaml"
    shutil.copyfile(workflow_src, workflow_dst)

    schema_src_dir = template_project_root / "artifacts" / "schemas"
    for pattern in ("*.schema.yaml", "*.schema.yml", "*.schema.json", "*.schema.md"):
        for src in sorted(schema_src_dir.glob(pattern), key=lambda p: p.name):
            shutil.copyfile(src, workspace_root / "artifacts" / "schemas" / src.name)

    _write_project_inputs(workspace_root)
    (workspace_root / "change_intent.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "CI-EXAMPLE-001",
                "title": "Deterministische Runtime-Workflow-Simulation",
                "created_at": FIXED_ARTIFACT_CREATED_AT,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )


def _write_project_inputs(workspace_root: Path) -> None:
    payload = "content: deterministic simulation input\n"
    for name in (
        "domain_scope.md",
        "domain_rules.md",
        "source_policy.md",
        "glossary.md",
        "architecture_contract.md",
    ):
        (workspace_root / name).write_text(payload, encoding="utf-8")


def _advance_once(ctx: RunContext, evaluator: GateEvaluator, schemas: dict[str, ArtifactSchema]) -> AdvanceResult:
    wf_engine = WorkflowEngine(ctx.workflow_def)
    return wf_engine.advance(
        ctx=ctx,
        evaluator=evaluator,
        decision_log_path=ctx.run_dir / "decision_log.yaml",
        schemas=schemas,
    )


def _materialize_state_artifacts(
    ctx: RunContext,
    schemas: dict[str, ArtifactSchema],
    invocation_layer: AgentInvocationLayer,
    decision_system: DecisionSystem,
    decisions: list[dict[str, Any]],
    known_decision_count: int,
    target_terminal_state: str,
) -> int:
    if ctx.current_state == "PLANNING":
        _write_implementation_plan(ctx.artifacts_dir / "implementation_plan.yaml")
        _write_design_tradeoffs(ctx.artifacts_dir / "design_tradeoffs.md")
        output_refs = _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_planner",
            inputs=("change_intent.yaml",),
            outputs=("implementation_plan.yaml", "design_tradeoffs.md"),
        )
        known_decision_count = _approve_refs(
            ctx=ctx,
            schemas=schemas,
            decision_system=decision_system,
            decisions=decisions,
            known_decision_count=known_decision_count,
            refs=output_refs,
        )
        return known_decision_count

    if ctx.current_state == "ARCH_CHECK":
        _write_arch_review_record(ctx.artifacts_dir / "arch_review_record.md")
        _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_architecture_guardian",
            inputs=("implementation_plan.yaml", "design_tradeoffs.md"),
            outputs=("arch_review_record.md",),
        )
        return known_decision_count

    if ctx.current_state == "TEST_DESIGN":
        _write_test_design(ctx.artifacts_dir / "test_design.yaml")
        output_refs = _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_test_designer",
            inputs=("implementation_plan.yaml", "design_tradeoffs.md"),
            outputs=("test_design.yaml",),
        )
        known_decision_count = _approve_refs(
            ctx=ctx,
            schemas=schemas,
            decision_system=decision_system,
            decisions=decisions,
            known_decision_count=known_decision_count,
            refs=output_refs,
        )
        return known_decision_count

    if ctx.current_state == "BRANCH_READY":
        _write_branch_status(ctx.artifacts_dir / "branch_status.md")
        _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_branch_manager",
            inputs=("implementation_plan.yaml",),
            outputs=("branch_status.md",),
        )
        return known_decision_count

    if ctx.current_state == "IMPLEMENTING":
        _write_implementation_summary(ctx.artifacts_dir / "implementation_summary.md")
        _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_implementer",
            inputs=("implementation_plan.yaml", "design_tradeoffs.md"),
            outputs=("implementation_summary.md",),
        )
        return known_decision_count

    if ctx.current_state == "TESTING":
        _write_test_report(ctx.artifacts_dir / "test_report.json", run_id=ctx.run_id)
        _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_test_runner",
            inputs=("test_design.yaml",),
            outputs=("test_report.json",),
        )
        return known_decision_count

    if ctx.current_state == "REVIEWING":
        _write_review_result(ctx.artifacts_dir / "review_result.md", outcome=target_terminal_state)
        output_refs = _invoke_human(
            ctx=ctx,
            schemas=schemas,
            invocation_layer=invocation_layer,
            role="agent_reviewer",
            inputs=("implementation_plan.yaml", "test_report.json"),
            outputs=("review_result.md",),
        )
        if target_terminal_state == "ACCEPTED_WITH_DEBT":
            known_decision_count = _approve_refs(
                ctx=ctx,
                schemas=schemas,
                decision_system=decision_system,
                decisions=decisions,
                known_decision_count=known_decision_count,
                refs=output_refs,
            )
        return known_decision_count

    return known_decision_count


def _invoke_human(
    ctx: RunContext,
    schemas: dict[str, ArtifactSchema],
    invocation_layer: AgentInvocationLayer,
    role: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
) -> tuple[ArtifactRef, ...]:
    contract = AgentContract(
        role_id=role,
        input_artifacts=inputs,
        output_artifacts=outputs,
        owned_artifacts=outputs,
        workflow_states=(ctx.current_state,),
    )
    result = invocation_layer.invoke(
        ctx=ctx,
        agent_role=role,
        agent_contracts={role: contract},
        schemas=schemas,
        mode=InvocationMode.HUMAN_AS_AGENT,
    )
    return result.output_refs


def _approve_refs(
    ctx: RunContext,
    schemas: dict[str, ArtifactSchema],
    decision_system: DecisionSystem,
    decisions: list[dict[str, Any]],
    known_decision_count: int,
    refs: tuple[ArtifactRef, ...],
) -> int:
    for ref in refs:
        decision_index = len(decisions) + 1
        decisions.append(
            {
                "decision_id": f"DEC-{decision_index:04d}",
                "timestamp": _decision_timestamp(decision_index),
                "human_identity": "human.simulation@example.local",
                "decision": "approve",
                "scope": f"gate_approval:{ref.name}",
                "references": [
                    {
                        "artifact": ref.name,
                        "artifact_id": ref.artifact_id,
                        "artifact_hash": ref.artifact_hash,
                    }
                ],
                "rationale": "Deterministic simulation approval.",
                "supersedes_decision_id": None,
            }
        )

    _write_decision_logs(ctx=ctx, decisions=decisions)
    decision_system.process_new_entries(
        ctx=ctx,
        decision_log_path=ctx.run_dir / "decision_log.yaml",
        last_known_count=known_decision_count,
        schemas=schemas,
    )
    return len(decisions)


def _write_decision_logs(ctx: RunContext, decisions: list[dict[str, Any]]) -> None:
    payload = {
        "schema_version": "v1",
        "decisions": decisions,
    }
    decision_yaml = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    (ctx.run_dir / "decision_log.yaml").write_text(decision_yaml, encoding="utf-8")
    (ctx.artifacts_dir / "decision_log.yaml").write_text(decision_yaml, encoding="utf-8")


def _decision_timestamp(index: int) -> str:
    base = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)
    return (base + timedelta(minutes=index)).isoformat()


def _write_implementation_plan(path: Path) -> None:
    payload = {
        "id": "PLAN-001",
        "supersedes_id": None,
        "created_at": FIXED_ARTIFACT_CREATED_AT,
        "inputs": {
            "change_intent_id": "CI-EXAMPLE-001",
            "architecture_contract_ref": "architecture_contract.md",
        },
        "plan_items": [
            {
                "id": "P-001",
                "title": "Implement deterministic simulation scaffold",
                "description": "Create reproducible sample run assets.",
                "dependencies": [],
                "outputs": ["implementation_summary.md"],
                "constraints": ["deterministic", "audit-ready"],
            }
        ],
        "non_goals": ["No implicit runtime behavior"],
        "risks": ["Schema drift in simulation assets"],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def _write_design_tradeoffs(path: Path) -> None:
    content = (
        "id: DT-001\n"
        "supersedes_id: null\n\n"
        "## Context\n"
        "- change_intent: CI-EXAMPLE-001\n"
        "- plan_ref: PLAN-001\n\n"
        "## Options considered\n"
        "- id: O-1\n"
        "  description: Human-as-agent deterministic invocation.\n"
        "  pros: reproducible events.\n"
        "  cons: no real model execution.\n"
        "  constraints: architecture_contract.md section-1\n\n"
        "## Decision\n"
        "- selected_option: O-1\n"
        "- rationale: deterministic replay first.\n\n"
        "## Assumptions\n"
        "- id: A-1\n"
        "  statement: Artifact schemas remain stable during run.\n"
        "  risk if false: gate failures.\n"
        "  how to validate: schema load before invocation.\n\n"
        "## Risks and mitigations\n"
        "- id: R-1\n"
        "  risk: missing schema file\n"
        "  mitigation: copy full schemas into workspace\n\n"
        "## Decision reference\n"
        "- decision_id: DEC-0001\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_arch_review_record(path: Path) -> None:
    content = (
        "id: AR-001\n"
        "supersedes_id: null\n"
        "outcome: PASS\n\n"
        "## Summary\n"
        "- reviewed: implementation_plan PLAN-001\n\n"
        "## Outcome\n"
        "- PASS\n\n"
        "## Findings\n"
        "- id: F-AR-1\n"
        "  contract_section: architecture_contract.md section-1\n"
        "  assessment: compliant\n"
        "  description: Planned change follows deterministic constraints.\n\n"
        "## Architecture change reference (only if `CHANGE_REQUIRED`)\n"
        "- not_applicable: true\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_test_design(path: Path) -> None:
    payload = {
        "id": "TD-001",
        "created_at": FIXED_ARTIFACT_CREATED_AT,
        "inputs": {
            "implementation_plan_id": "PLAN-001",
            "domain_rules_ref": "domain_rules.md",
        },
        "test_cases": [
            {
                "id": "TC-001",
                "title": "Workflow gate pass path",
                "purpose": "Validate deterministic transition progression.",
                "maps_to": {
                    "plan_items": ["P-001"],
                    "domain_rules": ["DR-001"],
                },
                "type": "integration",
                "steps": ["run simulation", "validate transition events"],
                "expected_result": "All required transitions are emitted.",
            }
        ],
        "coverage_notes": ["Covers state progression and event emission."],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def _write_branch_status(path: Path) -> None:
    content = (
        "id: BR-001\n"
        "supersedes_id: null\n\n"
        "## Summary\n"
        "- prepared isolated simulation workspace.\n\n"
        "## Base reference\n"
        "- base: simulation-template-v1\n\n"
        "## Change surface identifier\n"
        "- surface: workspace/default\n\n"
        "## Steps performed\n"
        "1. create workspace\n"
        "2. copy workflow and schemas\n"
        "3. initialize run\n\n"
        "## Issues / conflicts (if any)\n"
        "- none\n\n"
        "## Decision record (if applicable)\n"
        "- none\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_implementation_summary(path: Path) -> None:
    content = (
        "id: IS-001\n"
        "supersedes_id: null\n\n"
        "## Summary\n"
        "- Simulated implementation artifacts were generated.\n\n"
        "## Inputs\n"
        "- implementation_plan: PLAN-001\n"
        "- design_tradeoffs: DT-001\n\n"
        "## Files changed\n"
        "- runtime_workflow_simulation.py\n\n"
        "## Plan mapping\n"
        "- P-001 -> simulation scaffolding\n\n"
        "## Deviations (if any)\n"
        "- none\n\n"
        "## Follow-ups (optional)\n"
        "- optional: add additional failure scenario fixtures.\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_test_report(path: Path, run_id: str) -> None:
    payload = {
        "run_id": run_id,
        "created_at": FIXED_ARTIFACT_CREATED_AT,
        "inputs": {
            "test_design_id": "TD-001",
        },
        "environment": {
            "os": "windows",
            "tool_versions": {
                "python": "3.x",
            },
        },
        "selection": {
            "mode": "all",
            "definition": "deterministic simulation scope",
        },
        "results": {
            "passed": 3,
            "failed": 0,
            "skipped": 0,
            "failures": [],
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_review_result(path: Path, outcome: str) -> None:
    content = (
        "id: RV-001\n"
        "supersedes_id: null\n"
        f"outcome: {outcome}\n\n"
        "## Summary\n"
        "- Reviewed simulated workflow outputs against deterministic contracts.\n\n"
        "## Outcome\n"
        f"- {outcome}\n\n"
        "## Evidence\n"
        "- implementation_plan.yaml PLAN-001\n"
        "- test_report.json (same run_id)\n"
        "- architecture_contract.md section-1\n\n"
        "## Findings\n"
        "- id: F-RV-1\n"
        "  type: note\n"
        "  severity: minor\n"
        "  traceability: plan item P-001\n"
        "  description: Simulation path is deterministic and auditable.\n\n"
        "## Debt (only if `ACCEPTED_WITH_DEBT`)\n"
        "- none\n\n"
        "## Decision reference\n"
        "- decision_id: DEC-9999 (not required for ACCEPTED/FAILED)\n"
    )
    path.write_text(content, encoding="utf-8")


def _build_quality_report(
    ctx: RunContext,
    metrics_payload: dict[str, Any],
    target_terminal_state: str,
    transition_trace: list[dict[str, str]],
    blocked_trace: list[dict[str, str]],
    induce_planning_block: bool,
    decision_count: int,
) -> dict[str, Any]:
    events = metrics_payload.get("events", [])
    invocation_records = metrics_payload.get("invocation_records", [])
    event_types = [str(event.get("event_type", "")) for event in events if isinstance(event, dict)]
    event_ids = {str(event.get("event_id", "")) for event in events if isinstance(event, dict)}

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "CHK-001",
            "name": "target_terminal_reached",
            "pass": ctx.current_state == target_terminal_state,
            "evidence": {"current_state": ctx.current_state, "target": target_terminal_state},
        }
    )

    required_event_types = {
        "run.started",
        "workflow.transition_checked",
        "workflow.transition_completed",
        "agent.invocation_started",
        "agent.invocation_completed",
        "artifact.created",
        "decision.recorded",
        "run.completed",
    }
    checks.append(
        {
            "id": "CHK-002",
            "name": "required_event_types_present",
            "pass": required_event_types.issubset(set(event_types)),
            "evidence": {
                "missing": sorted(required_event_types.difference(set(event_types))),
                "present_count": len(set(event_types)),
            },
        }
    )

    if induce_planning_block:
        checks.append(
            {
                "id": "CHK-003",
                "name": "planning_block_observed",
                "pass": "run.blocked" in event_types,
                "evidence": {"blocked_trace": blocked_trace},
            }
        )
    else:
        checks.append(
            {
                "id": "CHK-003",
                "name": "planning_block_skipped_by_config",
                "pass": True,
                "evidence": {"induce_planning_block": False},
            }
        )

    started = event_types.count("agent.invocation_started")
    completed = event_types.count("agent.invocation_completed")
    checks.append(
        {
            "id": "CHK-004",
            "name": "invocation_event_balance",
            "pass": started == completed == len(invocation_records),
            "evidence": {
                "started_events": started,
                "completed_events": completed,
                "invocation_records": len(invocation_records),
            },
        }
    )

    causation_ok = True
    for event in events:
        if not isinstance(event, dict):
            continue
        causation = event.get("causation_event_id")
        if causation is None:
            continue
        if str(causation) not in event_ids:
            causation_ok = False
            break
    checks.append(
        {
            "id": "CHK-005",
            "name": "causation_links_resolve",
            "pass": causation_ok,
            "evidence": {"event_count": len(events)},
        }
    )

    artifact_events = [e for e in events if isinstance(e, dict) and e.get("event_type") == "artifact.created"]
    all_hashes_present = True
    for event in artifact_events:
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            all_hashes_present = False
            break
        artifact_hash = payload.get("artifact_hash")
        if not isinstance(artifact_hash, str) or not artifact_hash:
            all_hashes_present = False
            break
    checks.append(
        {
            "id": "CHK-006",
            "name": "artifact_hashes_present",
            "pass": all_hashes_present,
            "evidence": {"artifact_created_events": len(artifact_events)},
        }
    )

    decision_events = event_types.count("decision.recorded")
    checks.append(
        {
            "id": "CHK-007",
            "name": "decision_events_match_decisions",
            "pass": decision_events == decision_count,
            "evidence": {"decision_events": decision_events, "decision_entries": decision_count},
        }
    )

    passed = all(bool(check["pass"]) for check in checks)
    return {
        "simulation_contract": {
            "responsibility": "Deterministic end-to-end workflow replay with explicit quality checks.",
            "inputs": {
                "workflow_name": ctx.workflow_def.workflow_id,
                "target_terminal_state": target_terminal_state,
                "induce_planning_block": induce_planning_block,
            },
            "outputs": {
                "run_id": ctx.run_id,
                "run_metrics_path": str((ctx.artifacts_dir / "run_metrics.json").resolve()),
                "report_path": str((ctx.artifacts_dir / "simulation_report.json").resolve()),
            },
            "assumptions": [
                "Artifact schemas are copied from template project.",
                "Agent invocations run in human_as_agent mode for reproducibility.",
                "Decision approvals are explicit and append-only.",
            ],
        },
        "result": {
            "pass": passed,
            "terminal_state": ctx.current_state,
            "transition_count": len(transition_trace),
            "blocked_count": len(blocked_trace),
        },
        "checks": checks,
        "transition_trace": transition_trace,
        "blocked_trace": blocked_trace,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runtime-workflow-simulation",
        description="Deterministic runtime workflow simulation for integration quality checks.",
    )
    default_template_root = Path(__file__).resolve().parents[1]
    default_workspace = default_template_root / "examples" / "runtime_simulation_workspace"
    parser.add_argument("--template-project-root", default=str(default_template_root))
    parser.add_argument("--workspace-root", default=str(default_workspace))
    parser.add_argument("--workflow", default="default_workflow")
    parser.add_argument(
        "--target-terminal-state",
        default="ACCEPTED",
        choices=("ACCEPTED", "ACCEPTED_WITH_DEBT", "FAILED"),
    )
    parser.add_argument("--induce-planning-block", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = SimulationConfig(
        template_project_root=Path(args.template_project_root).resolve(),
        workspace_root=Path(args.workspace_root).resolve(),
        workflow_name=args.workflow,
        target_terminal_state=args.target_terminal_state,
        induce_planning_block=bool(args.induce_planning_block),
    )
    report = run_simulation(config)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
