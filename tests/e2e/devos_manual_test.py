"""
DevOS manual full-workflow e2e test using planning as implemented.

Responsibilities:
- load and validate the canonical planning artifact via PlanningEngine
- select the feature story from parsed planning models (no synthetic slicing)
- execute full runtime workflow with deterministic gate artifacts

Input contract:
- `FEATURE` fields: id, title, problem_statement, goals, constraints
- `.devOS/planning/project_plan.yaml` (or legacy fallback) is present and valid
- feature title must match exactly one planning story name (case-insensitive)
- required project inputs exist under `.devOS/project_inputs/` (canonical) or repo root (legacy fallback)

Output contract:
- writes `change_intent.yaml` at repo root
- creates a runtime run under `runs/RUN-<YYYYMMDD>-<NNNN>/`
- writes required gate artifacts under `runs/<run_id>/artifacts/`
- writes `decision_log.yaml` (run root + artifacts copy) for approval gates
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from capabilities.planning.planning_engine import DEFAULT_PROJECT_PLAN_PATH, PlanValidationError, PlanningEngine
from capabilities.planning.planning_models import ProjectModel, StoryModel, TaskModel
from kernel.engine.gate_evaluator import GateEvaluator
from kernel.engine.run_engine import RunEngine
from kernel.engine.workflow_engine import WorkflowEngine
from kernel.framework.schema_loader import load_all_schemas
from kernel.store.file_store import sha256_from_disk
from kernel.types.run import RunContext, TERMINAL_STATES


REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGE_INTENT_PATH = REPO_ROOT / "change_intent.yaml"
CHANGE_INTENT_CREATED_AT = "2026-03-15T00:00:00+00:00"
REQUESTED_BY = "manual.e2e.script"
DECISION_TIME_BASE = datetime(2026, 3, 15, 0, 10, tzinfo=timezone.utc)
REQUIRED_PROJECT_INPUTS: tuple[str, ...] = (
    "domain_scope.md",
    "domain_rules.md",
    "source_policy.md",
    "glossary.md",
    "architecture_contract.md",
)

FEATURE = {
    "id": "feature_feature_spec_artifact",
    "title": "Introduce feature_spec artifact",
    "problem_statement": """
    Feature discussions currently occur in chat but there is no
    structured artifact capturing the agreed feature definition.
    This leads to unclear planning input.
    """,
    "goals": [
        "Introduce a feature_spec artifact",
        "Store feature definitions before planning begins",
    ],
    "constraints": [
        "Must integrate with the existing planning layer",
        "Must not break current project_plan schema",
    ],
}


def run_planning_and_select_story(feature: dict[str, Any]) -> tuple[ProjectModel, StoryModel]:
    print("\n=== PLANNING VALIDATION ===")
    engine = PlanningEngine()
    result = engine.load_and_validate(lint_mode="enforce")
    project = result.project
    print(f"Planning project: {project.name}")
    print(f"Lint violations: {len(result.violations)}")
    print(f"Epic count: {len(project.epics)}")

    print("\n=== STORY SELECTION FROM PLANNING MODEL ===")
    story = _select_story_for_feature(project, feature)
    print(f"Selected story: {story.name}")
    print(f"Selected task count: {len(story.tasks)}")
    return project, story


def write_change_intent(project: ProjectModel, story: StoryModel, feature: dict[str, Any]) -> Path:
    print("\n=== WRITE CHANGE INTENT ===")
    change_intent = build_change_intent(project=project, story=story, feature=feature)
    CHANGE_INTENT_PATH.write_text(
        yaml.safe_dump(change_intent, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    print(f"Change intent written: {CHANGE_INTENT_PATH}")
    print(f"Change intent id: {change_intent['id']}")
    return CHANGE_INTENT_PATH


def initialize_runtime(change_intent_path: Path) -> tuple[RunEngine, RunContext]:
    print("\n=== RUNTIME INITIALIZE ===")
    run_engine = RunEngine()
    ctx = run_engine.initialize_run(
        project_root=REPO_ROOT,
        change_intent_path=change_intent_path,
        workflow_name="default_workflow",
    )
    print(f"Run ID: {ctx.run_id}")
    print(f"Initial state: {ctx.current_state}")
    print(f"Run directory: {ctx.run_dir}")
    print(f"Artifacts directory: {ctx.artifacts_dir}")
    return run_engine, ctx


def execute_full_workflow(
    run_engine: RunEngine,
    ctx: RunContext,
    feature: dict[str, Any],
    story: StoryModel,
) -> RunContext:
    print("\n=== EXECUTE FULL WORKFLOW ===")
    _require_project_inputs(ctx.project_inputs_root or ctx.project_root)

    schemas = load_all_schemas(ctx.project_root / "artifacts" / "schemas")
    evaluator = GateEvaluator()
    workflow_engine = WorkflowEngine(ctx.workflow_def)
    decisions: list[dict[str, Any]] = []

    hop_limit = 32
    hops = 0
    while ctx.current_state not in TERMINAL_STATES and hops < hop_limit:
        hops += 1
        _materialize_state_artifacts(
            ctx=ctx,
            feature=feature,
            story=story,
            decisions=decisions,
        )
        advance = workflow_engine.advance(
            ctx=ctx,
            evaluator=evaluator,
            decision_log_path=ctx.run_dir / "decision_log.yaml",
            schemas=schemas,
        )
        if not advance.transitioned or not advance.new_state:
            raise RuntimeError(
                f"Workflow blocked at state '{ctx.current_state}'. "
                f"Gate failures: {_failed_checks_text(advance)}"
            )
        print(f"Transition: {ctx.current_state} -> {advance.new_state}")
        ctx = replace(ctx, current_state=advance.new_state)

    if ctx.current_state not in TERMINAL_STATES:
        raise RuntimeError(f"Workflow exceeded hop limit ({hop_limit}) at state '{ctx.current_state}'.")

    run_engine.declare_terminal(ctx, ctx.current_state)
    print(f"Terminal state reached: {ctx.current_state}")
    return ctx


def _materialize_state_artifacts(
    *,
    ctx: RunContext,
    feature: dict[str, Any],
    story: StoryModel,
    decisions: list[dict[str, Any]],
) -> None:
    artifacts_dir = ctx.artifacts_dir
    feature_id = _require_non_empty_str(feature, "id")
    plan_items = _build_plan_items_from_story(story, feature_id)

    if ctx.current_state == "PLANNING":
        _write_yaml(
            artifacts_dir / "implementation_plan.yaml",
            {
                "id": "PLAN-MANUAL-E2E-001",
                "supersedes_id": None,
                "created_at": CHANGE_INTENT_CREATED_AT,
                "inputs": {
                    "change_intent_id": f"CI-{feature_id}",
                    "architecture_contract_ref": "architecture_contract.md",
                },
                "plan_items": plan_items,
                "non_goals": ["No workflow definition changes."],
                "risks": ["Potential schema drift if artifact contracts change."],
            },
        )
        _write_markdown(
            artifacts_dir / "design_tradeoffs.md",
            (
                "id: DT-MANUAL-E2E-001\n"
                "supersedes_id: null\n\n"
                "## Context\n"
                f"- change_intent: CI-{feature_id}\n"
                "- plan_ref: PLAN-MANUAL-E2E-001\n\n"
                "## Options considered\n"
                "- id: O-1\n"
                "  description: Implement feature using selected planning story/task set.\n"
                "  pros: aligns runtime execution with canonical planning model.\n"
                "  cons: depends on story availability in project plan.\n"
                "  constraints: architecture_contract.md section-1\n\n"
                "## Decision\n"
                "- selected_option: O-1\n"
                "- rationale: planning-first execution is deterministic and auditable.\n\n"
                "## Assumptions\n"
                "- id: A-1\n"
                "  statement: selected planning story remains stable for this run.\n"
                "  risk if false: implementation plan no longer maps to planning artifact.\n"
                "  how to validate: select story by exact name before run initialization.\n\n"
                "## Risks and mitigations\n"
                "- id: R-1\n"
                "  risk: missing verification task\n"
                "  mitigation: enforce at least one verification task in selected story\n\n"
                "## Decision reference\n"
                "- decision_id: DEC-MANUAL-E2E-0001\n"
            ),
        )
        _append_approval_for_artifact(decisions, ctx, "implementation_plan.yaml")
        _append_approval_for_artifact(decisions, ctx, "design_tradeoffs.md")
        _write_decision_log(ctx, decisions)
        return

    if ctx.current_state == "ARCH_CHECK":
        _write_markdown(
            artifacts_dir / "arch_review_record.md",
            (
                "id: AR-MANUAL-E2E-001\n"
                "supersedes_id: null\n"
                "outcome: PASS\n\n"
                "## Summary\n"
                "- reviewed implementation_plan PLAN-MANUAL-E2E-001.\n\n"
                "## Outcome\n"
                "- PASS\n\n"
                "## Findings\n"
                "- id: F-AR-001\n"
                "  contract_section: architecture_contract.md section-1\n"
                "  assessment: compliant\n"
                "  description: Planned change follows deterministic architecture boundary.\n\n"
                "## Architecture change reference (only if `CHANGE_REQUIRED`)\n"
                "- not_applicable: true\n"
            ),
        )
        return

    if ctx.current_state == "TEST_DESIGN":
        verification_task = _find_verification_task(story)
        _write_yaml(
            artifacts_dir / "test_design.yaml",
            {
                "id": "TD-MANUAL-E2E-001",
                "created_at": CHANGE_INTENT_CREATED_AT,
                "inputs": {
                    "implementation_plan_id": "PLAN-MANUAL-E2E-001",
                    "domain_rules_ref": "domain_rules.md",
                },
                "test_cases": [
                    {
                        "id": "TC-E2E-001",
                        "title": verification_task.name,
                        "purpose": verification_task.description,
                        "maps_to": {
                            "plan_items": [plan_items[0]["id"]],
                            "domain_rules": ["DR-001"],
                        },
                        "type": "e2e",
                        "steps": [
                            "materialize required gate artifacts",
                            "advance workflow state by state",
                            "verify terminal acceptance",
                        ],
                        "expected_result": "Run reaches ACCEPTED without blocked transitions.",
                    }
                ],
                "coverage_notes": ["Covers all delivery workflow gates in default_workflow."],
            },
        )
        _append_approval_for_artifact(decisions, ctx, "test_design.yaml")
        _write_decision_log(ctx, decisions)
        return

    if ctx.current_state == "BRANCH_READY":
        _write_markdown(
            artifacts_dir / "branch_status.md",
            (
                "id: BR-MANUAL-E2E-001\n"
                "supersedes_id: null\n\n"
                "## Summary\n"
                "- Prepared isolated manual test change surface.\n\n"
                "## Base reference\n"
                "- base: main\n\n"
                "## Change surface identifier\n"
                "- surface: manual-e2e-workspace\n\n"
                "## Steps performed\n"
                "1. validate planning artifact\n"
                "2. select story from planning model\n"
                "3. initialize runtime run\n\n"
                "## Issues / conflicts (if any)\n"
                "- none\n\n"
                "## Decision record (if applicable)\n"
                "- none\n"
            ),
        )
        return

    if ctx.current_state == "IMPLEMENTING":
        _write_markdown(
            artifacts_dir / "implementation_summary.md",
            (
                "id: IS-MANUAL-E2E-001\n"
                "supersedes_id: null\n\n"
                "## Summary\n"
                "- Simulated implementation from selected planning story.\n\n"
                "## Inputs\n"
                "- implementation_plan: PLAN-MANUAL-E2E-001\n"
                "- design_tradeoffs: DT-MANUAL-E2E-001\n\n"
                "## Files changed\n"
                "- tests/e2e/devos_manual_test.py\n\n"
                "## Plan mapping\n"
                f"- {plan_items[0]['id']} -> selected story/task execution path\n\n"
                "## Deviations (if any)\n"
                "- none\n"
            ),
        )
        return

    if ctx.current_state == "TESTING":
        _write_json(
            artifacts_dir / "test_report.json",
            {
                "run_id": ctx.run_id,
                "created_at": CHANGE_INTENT_CREATED_AT,
                "inputs": {"test_design_id": "TD-MANUAL-E2E-001"},
                "environment": {"os": "windows", "tool_versions": {"python": "3.x"}},
                "selection": {"mode": "all", "definition": "manual e2e full workflow"},
                "results": {"passed": 1, "failed": 0, "skipped": 0, "failures": []},
            },
        )
        return

    if ctx.current_state == "REVIEWING":
        _write_markdown(
            artifacts_dir / "review_result.md",
            (
                "id: RV-MANUAL-E2E-001\n"
                "supersedes_id: null\n"
                "outcome: ACCEPTED\n\n"
                "## Summary\n"
                "- Reviewed selected planning story execution and runtime evidence.\n\n"
                "## Outcome\n"
                "- ACCEPTED\n\n"
                "## Evidence\n"
                "- implementation_plan.yaml PLAN-MANUAL-E2E-001\n"
                "- test_report.json (same run_id)\n"
                "- architecture_contract.md section-1\n\n"
                "## Findings\n"
                "- id: F-RV-001\n"
                "  type: note\n"
                "  severity: minor\n"
                f"  traceability: story:{story.name}\n"
                "  description: Workflow path is deterministic and traceable.\n\n"
                "## Debt (only if `ACCEPTED_WITH_DEBT`)\n"
                "- not_applicable: true\n\n"
                "## Decision reference\n"
                "- not_required_for: ACCEPTED\n"
            ),
        )
        return


def _build_plan_items_from_story(story: StoryModel, feature_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not story.tasks:
        raise ValueError(f"Selected story '{story.name}' has no tasks.")
    for idx, task in enumerate(story.tasks, start=1):
        item_id = f"P-{idx:03d}"
        items.append(
            {
                "id": item_id,
                "title": task.name,
                "description": task.description or f"Task for story {story.name}",
                "dependencies": [],
                "outputs": [f"task:{task.name}", f"feature:{feature_id}"],
                "constraints": [story.constraints or "No additional constraints provided."],
            }
        )
    return items


def _select_story_for_feature(project: ProjectModel, feature: dict[str, Any]) -> StoryModel:
    target = _require_non_empty_str(feature, "title").casefold()
    matches: list[StoryModel] = []
    for epic in project.epics:
        for story in epic.stories:
            if story.name.casefold() == target:
                matches.append(story)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Feature title maps to multiple stories: {feature['title']!r}")
    available = sorted(story.name for epic in project.epics for story in epic.stories)
    raise ValueError(
        f"No planning story found for feature title {feature['title']!r}. "
        f"Available stories: {available}"
    )


def _find_verification_task(story: StoryModel) -> TaskModel:
    for task in story.tasks:
        if task.task_type and task.task_type.strip().lower() == "verification":
            return task
    raise ValueError(f"Selected story '{story.name}' has no verification task.")


def _append_approval_for_artifact(
    decisions: list[dict[str, Any]],
    ctx: RunContext,
    artifact_name: str,
) -> None:
    artifact_path = ctx.artifacts_dir / artifact_name
    artifact_id = _read_top_level_id(artifact_path)
    if artifact_id is None:
        raise ValueError(f"Cannot approve artifact without id: {artifact_name}")
    decision_index = len(decisions) + 1
    decisions.append(
        {
            "decision_id": f"DEC-MANUAL-E2E-{decision_index:04d}",
            "timestamp": (DECISION_TIME_BASE + timedelta(minutes=decision_index)).isoformat(),
            "human_identity": REQUESTED_BY,
            "decision": "approve",
            "scope": f"gate_approval:{artifact_name}",
            "references": [
                {
                    "artifact": artifact_name,
                    "artifact_id": artifact_id,
                    "artifact_hash": sha256_from_disk(artifact_path),
                }
            ],
            "rationale": "Deterministic manual e2e approval.",
            "supersedes_decision_id": None,
        }
    )


def _write_decision_log(ctx: RunContext, decisions: list[dict[str, Any]]) -> None:
    payload = {"schema_version": "v1", "decisions": decisions}
    _write_yaml(ctx.run_dir / "decision_log.yaml", payload)
    _write_yaml(ctx.artifacts_dir / "decision_log.yaml", payload)


def _failed_checks_text(advance: Any) -> str:
    if advance.gate_result is None:
        return "no gate result"
    failed = [check for check in advance.gate_result.checks if check.result.value == "fail"]
    if not failed:
        return "unknown"
    parts = [f"{check.check_type.value}:{check.subject}:{check.detail or 'failed'}" for check in failed]
    return "; ".join(parts)


def _require_project_inputs(project_inputs_root: Path) -> None:
    missing = [name for name in REQUIRED_PROJECT_INPUTS if not (project_inputs_root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required project input files in '{project_inputs_root}': {', '.join(missing)}"
        )


def _read_top_level_id(path: Path) -> str | None:
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        value = data.get("id") if isinstance(data, dict) else None
        return str(value).strip() if value is not None else None
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        value = data.get("id") if isinstance(data, dict) else None
        return str(value).strip() if value is not None else None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "id":
            cleaned = value.strip()
            return cleaned if cleaned else None
    return None


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_markdown(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_change_intent(project: ProjectModel, story: StoryModel, feature: dict[str, Any]) -> dict[str, Any]:
    feature_id = _require_non_empty_str(feature, "id")
    problem_statement = _clean_multiline(_require_non_empty_str(feature, "problem_statement"))
    constraints = _require_non_empty_str_list(feature, "constraints")
    acceptance_criteria = _extract_acceptance_criteria(story, feature)

    must_haves, must_not = _split_constraints(constraints)
    if not must_haves:
        must_haves = ["Implement the feature exactly as requested."]
    if not must_not:
        must_not = ["Do not expand scope beyond explicitly listed goals."]

    summary = f"{story.name}. {problem_statement}"
    return {
        "id": f"CI-{feature_id}",
        "created_at": CHANGE_INTENT_CREATED_AT,
        "requested_by": REQUESTED_BY,
        "summary": summary,
        "scope": {
            "in_scope": acceptance_criteria,
            "out_of_scope": [
                "Do not change runtime workflow definitions.",
                "Do not alter unrelated planning stories.",
            ],
        },
        "constraints": {
            "must_haves": must_haves,
            "must_not": must_not,
        },
        "acceptance_criteria": acceptance_criteria,
        "references": [
            {"name": "planning_artifact", "location": str(DEFAULT_PROJECT_PLAN_PATH)},
            {"name": "planning_project", "location": project.name},
            {"name": "planning_story", "location": story.name},
            {"name": "feature_definition", "location": f"feature:{feature_id}"},
        ],
    }


def _extract_acceptance_criteria(story: StoryModel, feature: dict[str, Any]) -> list[str]:
    story_criteria = story.acceptance_criteria or ""
    checklist = [
        line.replace("- [ ]", "", 1).strip()
        for line in story_criteria.splitlines()
        if line.strip().startswith("- [ ]")
    ]
    if checklist:
        return checklist
    return _require_non_empty_str_list(feature, "goals")


def _split_constraints(constraints: list[str]) -> tuple[list[str], list[str]]:
    must_haves: list[str] = []
    must_not: list[str] = []
    for item in constraints:
        normalized = item.strip()
        lower = normalized.casefold()
        if lower.startswith("must not "):
            must_not.append(normalized[9:].strip() or normalized)
        elif lower.startswith("must "):
            must_haves.append(normalized[5:].strip() or normalized)
        else:
            must_haves.append(normalized)
    return must_haves, must_not


def _require_non_empty_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Feature field '{key}' must be a non-empty string.")
    return value.strip()


def _require_non_empty_str_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Feature field '{key}' must be a non-empty list of strings.")
    result: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Feature field '{key}[{idx}]' must be a non-empty string.")
        result.append(item.strip())
    return result


def _clean_multiline(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return " ".join(lines)


def main() -> int:
    print("DevOS Manual E2E Test")
    try:
        print(f"Feature id: {FEATURE['id']}")
        print(f"Feature title: {FEATURE['title']}")
        project, story = run_planning_and_select_story(FEATURE)
        change_intent_path = write_change_intent(project, story, FEATURE)
        run_engine, ctx = initialize_runtime(change_intent_path)
        final_ctx = execute_full_workflow(run_engine, ctx, FEATURE, story)
        print(f"Final state: {final_ctx.current_state}")
    except (FileNotFoundError, ValueError, PlanValidationError, RuntimeError) as exc:
        print(f"Manual test failed: {exc}")
        return 1
    print("\nManual test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
