"""
DevOS planning engine (tool-agnostic).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .planning_models import ProjectModel
from .planning_parser import parse_planning_yaml
from .work_item_linter import LintViolation, lint_project


DEFAULT_PROJECT_PLAN_PATH = Path(".devOS/planning/project_plan.yaml")
LEGACY_PROJECT_PLAN_PATH = Path(".devos/planning/project_plan.yaml")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class PlanValidationError(ValueError):
    def __init__(self, violations: list[LintViolation]) -> None:
        self.violations = tuple(violations)
        joined = "\n".join(f"  - [{v.rule_id}] {v.context}: {v.message}" for v in violations)
        super().__init__(
            f"Project plan validation failed with {len(violations)} violation(s):\n{joined}"
        )


@dataclass(frozen=True)
class PlanningValidationResult:
    project: ProjectModel
    violations: tuple[LintViolation, ...]


class PlanningEngine:
    def load_project_plan(self, plan_path: str | Path = DEFAULT_PROJECT_PLAN_PATH) -> ProjectModel:
        return parse_planning_yaml(str(_resolve_plan_path(plan_path)))

    def validate_project_plan(self, project: ProjectModel) -> tuple[LintViolation, ...]:
        return tuple(lint_project(project))

    def load_and_validate(
        self,
        plan_path: str | Path = DEFAULT_PROJECT_PLAN_PATH,
        *,
        lint_mode: str = "enforce",
    ) -> PlanningValidationResult:
        if lint_mode not in {"enforce", "warn"}:
            raise ValueError("lint_mode must be 'enforce' or 'warn'.")
        project = self.load_project_plan(plan_path)
        violations = self.validate_project_plan(project)
        if violations and lint_mode == "enforce":
            raise PlanValidationError(list(violations))
        return PlanningValidationResult(project=project, violations=violations)


def _resolve_plan_path(plan_path: str | Path) -> Path:
    candidate = Path(plan_path)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = candidate.resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    repo_candidate = (_REPO_ROOT / candidate).resolve()
    if repo_candidate.exists():
        return repo_candidate

    # Compatibility fallback so existing repos using lowercase `.devos` keep working.
    if candidate == DEFAULT_PROJECT_PLAN_PATH:
        legacy_cwd = LEGACY_PROJECT_PLAN_PATH.resolve()
        if legacy_cwd.exists():
            return legacy_cwd
        legacy_repo = (_REPO_ROOT / LEGACY_PROJECT_PLAN_PATH).resolve()
        if legacy_repo.exists():
            return legacy_repo

    return cwd_candidate

