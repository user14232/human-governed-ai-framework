"""
CLI entry point for the Linear project creator.

Usage:
    python main.py <yaml_file> [--dry-run] [--verbose] [--output <path>]

Arguments:
    yaml_file           Path to the YAML project definition file.

Options:
    --dry-run           Log what would be created without calling the Linear API.
    --verbose           Set log level to DEBUG (default: INFO).
    --output <path>     Path for the output mapping JSON file.
                        Default: linear_mapping.json in the current directory.

Exit codes:
    0  All objects created successfully (or dry-run completed successfully).
    1  Configuration error, YAML validation error, or API error.

Environment variables required (unless --dry-run):
    LINEAR_API_KEY   Linear personal or application API key.
    LINEAR_TEAM_ID   Linear team identifier (UUID).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from config import load_config
from linear_client import LinearAPIError, LinearClient
from models import ProjectModel
from project_builder import build_project
from yaml_parser import parse_yaml


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI definition
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linear_project_creator",
        description="Create a Linear project hierarchy from a YAML definition file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "yaml_file",
        metavar="YAML_FILE",
        help="Path to the project definition YAML file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log what would be created without calling the Linear API.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default="linear_mapping.json",
        help="Output path for the Linear ID mapping file (default: linear_mapping.json).",
    )
    return parser


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def _print_summary(mapping: dict, dry_run: bool) -> None:
    mode_label = " [DRY-RUN]" if dry_run else ""
    print(f"\n=== Linear Project Creator — Summary{mode_label} ===")
    print(f"  Project ID  : {mapping['project']}")
    print(f"  Milestones  : {len(mapping.get('milestones', {}))}")
    print(f"  Epics       : {len(mapping['epics'])}")
    print(f"  Stories     : {len(mapping['stories'])}")
    print(f"  Tasks       : {len(mapping['tasks'])}")

    if mapping.get("milestones"):
        print("\n  Milestones created:")
        for name, ms_id in mapping["milestones"].items():
            print(f"    {ms_id}  {name}")

    if mapping["epics"]:
        print("\n  Epics created:")
        for name, issue_id in mapping["epics"].items():
            print(f"    {issue_id}  {name}")

    print()


def _write_mapping(mapping: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("Mapping written to %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)

    output_path = Path(args.output).resolve()

    # ------------------------------------------------------------------
    # Step 1: Parse YAML input — fail fast, no API calls yet.
    # ------------------------------------------------------------------
    logger.info("Parsing input file: %s", args.yaml_file)
    try:
        project: ProjectModel = parse_yaml(args.yaml_file)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except (ValueError, Exception) as exc:
        logger.error("YAML parse error: %s", exc)
        return 1

    logger.info(
        "Parsed: project='%s', %d epic(s).",
        project.name,
        len(project.epics),
    )

    # ------------------------------------------------------------------
    # Step 2: Load config — required even in dry-run so the user sees
    # config errors early rather than at the end of a dry-run.
    # In dry-run, we catch the error and proceed with a None client.
    # ------------------------------------------------------------------
    client: LinearClient | None = None
    if not args.dry_run:
        try:
            config = load_config()
        except ValueError as exc:
            logger.error("Configuration error: %s", exc)
            return 1
        client = LinearClient(config)
        logger.info("Linear client initialised (team_id=%s).", config.team_id)
        team_id = config.team_id
    else:
        # Attempt to load config; if it's missing, warn but continue for dry-run.
        try:
            config = load_config()
            client = LinearClient(config)
            team_id = config.team_id
        except ValueError as exc:
            logger.warning(
                "Config incomplete (%s) — proceeding in dry-run mode without a real client.",
                exc,
            )
            team_id = "dry-run-team"
            client = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Step 3: Build the project hierarchy.
    # ------------------------------------------------------------------
    logger.info("Starting project build (dry_run=%s).", args.dry_run)

    # Pass flush_path so progress is persisted after each epic even on failure.
    try:
        mapping = build_project(
            project=project,
            client=client,  # type: ignore[arg-type]  # safe: dry_run guards API calls
            team_id=team_id,
            dry_run=args.dry_run,
            flush_path=output_path,
        )
    except LinearAPIError as exc:
        logger.error("Linear API error: %s", exc)
        logger.info(
            "Partial mapping (if any) was flushed to %s before the error.", output_path
        )
        return 1

    # ------------------------------------------------------------------
    # Step 4: Write final mapping and print summary.
    # ------------------------------------------------------------------
    try:
        _write_mapping(mapping, output_path)
    except OSError as exc:
        logger.error("Could not write mapping file: %s", exc)
        return 1

    _print_summary(mapping, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
