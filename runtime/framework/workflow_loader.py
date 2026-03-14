from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from runtime.types.workflow import RequiresBlock, Transition, WorkflowDefinition


class ParseError(ValueError):
    """Raised when a framework contract file cannot be parsed deterministically."""


def load_workflow(workflow_path: Path) -> WorkflowDefinition:
    """Parse a workflow YAML file and return a typed workflow definition."""
    data = _read_yaml_mapping(workflow_path)

    workflow_id = _required_str(data, "id", workflow_path)
    version = _required_str(data, "version", workflow_path)
    states = tuple(_required_str_list(data, "states", workflow_path))
    transitions_raw = _required_list(data, "transitions", workflow_path)
    transitions = tuple(
        _parse_transition(item, workflow_path, idx) for idx, item in enumerate(transitions_raw)
    )

    artifacts_used = tuple(_optional_str_list(data, "artifacts_used", workflow_path))
    return WorkflowDefinition(
        workflow_id=workflow_id,
        version=version,
        states=states,
        transitions=transitions,
        artifacts_used=artifacts_used,
    )


def _parse_transition(raw: Any, workflow_path: Path, index: int) -> Transition:
    if not isinstance(raw, dict):
        raise ParseError(f"{workflow_path}: transition[{index}] must be a mapping.")

    from_state = _required_str(raw, "from", workflow_path)
    to_state = _required_str(raw, "to", workflow_path)
    notes = _optional_str(raw, "notes", workflow_path)

    requires_raw = raw.get("requires", {})
    if requires_raw is None:
        requires_raw = {}
    if not isinstance(requires_raw, dict):
        raise ParseError(f"{workflow_path}: transition[{index}].requires must be a mapping.")

    inputs_present = requires_raw.get("inputs_present")
    if inputs_present is not None and not isinstance(inputs_present, bool):
        raise ParseError(
            f"{workflow_path}: transition[{index}].requires.inputs_present must be bool."
        )

    artifacts = tuple(_optional_str_list(requires_raw, "artifacts", workflow_path))
    human_approval = tuple(_optional_str_list(requires_raw, "human_approval", workflow_path))

    conditions_raw = requires_raw.get("conditions", {})
    if conditions_raw is None:
        conditions_raw = {}
    if not isinstance(conditions_raw, dict):
        raise ParseError(f"{workflow_path}: transition[{index}].requires.conditions must be a mapping.")
    conditions: dict[str, str] = {}
    for key, value in conditions_raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ParseError(
                f"{workflow_path}: transition[{index}].requires.conditions entries must be string->string."
            )
        conditions[key] = value

    requires = RequiresBlock(
        inputs_present=inputs_present,
        artifacts=artifacts,
        human_approval=human_approval,
        conditions=conditions,
    )
    return Transition(from_state=from_state, to_state=to_state, requires=requires, notes=notes)


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Could not read workflow file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError(f"{path}: top-level YAML must be a mapping.")
    return data


def _required_str(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ParseError(f"{path}: required string field '{key}' missing or empty.")
    return value


def _optional_str(data: dict[str, Any], key: str, path: Path) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ParseError(f"{path}: optional field '{key}' must be a string.")
    return value


def _required_list(data: dict[str, Any], key: str, path: Path) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ParseError(f"{path}: required list field '{key}' missing or invalid.")
    return value


def _required_str_list(data: dict[str, Any], key: str, path: Path) -> list[str]:
    raw = _required_list(data, key, path)
    result: list[str] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ParseError(f"{path}: '{key}[{idx}]' must be a non-empty string.")
        result.append(item)
    return result


def _optional_str_list(data: dict[str, Any], key: str, path: Path) -> list[str]:
    if key not in data or data.get(key) is None:
        return []
    value = data.get(key)
    if not isinstance(value, list):
        raise ParseError(f"{path}: optional list field '{key}' must be a list.")
    result: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ParseError(f"{path}: '{key}[{idx}]' must be a non-empty string.")
        result.append(item)
    return result

