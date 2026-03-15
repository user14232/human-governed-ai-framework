"""
DevOS planning CLI.

Workflow:
1) Parse and validate the planning artifact.
2) Optionally sync it to an external provider (currently Linear).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from capabilities.planning.planning_engine import (
    DEFAULT_PROJECT_PLAN_PATH,
    PlanValidationError,
    PlanningEngine,
)
from capabilities.planning.work_item_linter import LintViolation
from capabilities.linear.config import load_config
from capabilities.linear.linear_client import LinearAPIError, LinearClient
from capabilities.linear.linear_provider import LinearProvider
from capabilities.linear.project_builder import BuildStats

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devos planning")
    parser.add_argument("--verbose", action="store_true", default=False)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("plan", nargs="?", default=str(DEFAULT_PROJECT_PLAN_PATH))
    validate.add_argument("--lint-mode", choices=("enforce", "warn"), default="enforce")

    sync = sub.add_parser("sync")
    sync.add_argument("provider", choices=("linear",))
    sync.add_argument("plan", nargs="?", default=str(DEFAULT_PROJECT_PLAN_PATH))
    sync.add_argument("--lint-mode", choices=("enforce", "warn"), default="enforce")
    sync.add_argument("--dry-run", action="store_true", default=False)
    sync.add_argument("--output", default="linear_mapping.json")

    return parser


def _report_lint_violations(violations: list[LintViolation], lint_mode: str) -> None:
    level_fn = logger.warning if lint_mode == "warn" else logger.error
    level_fn("Planning validation failed with %d violation(s).", len(violations))
    for v in violations:
        level_fn("  [%s] %s - %s", v.rule_id, v.context, v.message)


def _write_mapping(mapping: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def _write_run_report(
    mapping: dict,
    stats: BuildStats,
    violations: list[LintViolation],
    lint_mode: str,
    output_path: Path,
) -> None:
    report = {
        "schema_version": "1",
        "lint": {
            "mode": lint_mode,
            "violation_count": len(violations),
            "violations": [
                {"context": v.context, "rule_id": v.rule_id, "message": v.message}
                for v in violations
            ],
        },
        "build": {
            "project_id": mapping.get("project", ""),
            "milestones_created": stats.milestones_created,
            "epics_created": stats.epics_created,
            "stories_created": stats.stories_created,
            "tasks_created": stats.tasks_created,
            "relations_created": stats.relations_created,
            "unresolved_blocks_count": len(stats.unresolved_blocks),
            "unresolved_blocks": stats.unresolved_blocks,
        },
    }
    report_path = output_path.with_name(output_path.stem + "_report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    engine = PlanningEngine()

    if args.command == "validate":
        try:
            result = engine.load_and_validate(args.plan, lint_mode=args.lint_mode)
        except PlanValidationError as exc:
            _report_lint_violations(list(exc.violations), args.lint_mode)
            return 1
        except (FileNotFoundError, ValueError) as exc:
            logger.error("%s", exc)
            return 1
        logger.info("Validation passed for project '%s'.", result.project.name)
        return 0

    # sync
    try:
        result = engine.load_and_validate(args.plan, lint_mode=args.lint_mode)
    except PlanValidationError as exc:
        _report_lint_violations(list(exc.violations), args.lint_mode)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    violations = list(result.violations)
    if violations:
        _report_lint_violations(violations, args.lint_mode)

    if args.provider != "linear":
        logger.error("Unsupported provider: %s", args.provider)
        return 1

    output = Path(args.output).resolve()
    if args.dry_run:
        team_id = "dry-run-team"
        client = None
    else:
        config = load_config()
        team_id = config.team_id
        client = LinearClient(config)

    provider = LinearProvider(client=client, team_id=team_id, dry_run=args.dry_run)  # type: ignore[arg-type]
    try:
        mapping, stats = provider.sync_project(result.project, flush_path=output)
    except LinearAPIError as exc:
        logger.error("Linear API error: %s", exc)
        return 1

    _write_mapping(mapping, output)
    _write_run_report(mapping, stats, violations, args.lint_mode, output)
    logger.info("Sync complete. Mapping written to %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

