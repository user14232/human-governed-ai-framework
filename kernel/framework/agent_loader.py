from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class ParseError(ValueError):
    """Raised when an agent contract cannot be parsed deterministically."""


@dataclass(frozen=True)
class AgentContract:
    role_id: str
    input_artifacts: tuple[str, ...]
    output_artifacts: tuple[str, ...]
    owned_artifacts: tuple[str, ...]
    workflow_states: tuple[str, ...]


def load_agent_contract(agent_path: Path) -> AgentContract:
    """Parse one agent markdown contract into a typed AgentContract."""
    text = _read_text(agent_path)
    role_id = _require_regex(text, r"\*\*role_id\*\*:\s*`([^`]+)`", agent_path, "role_id")
    workflow_scope = _extract_workflow_scope(text, agent_path)

    input_artifacts = _extract_artifact_names(_slice_section(text, "## Inputs"))
    output_artifacts = _extract_artifact_names(_slice_section(text, "## Outputs"))
    write_policy_artifacts = _extract_artifact_names(_slice_section(text, "## Write policy"))

    owned = sorted(set(output_artifacts).union(write_policy_artifacts))

    return AgentContract(
        role_id=role_id,
        input_artifacts=tuple(sorted(set(input_artifacts))),
        output_artifacts=tuple(sorted(set(output_artifacts))),
        owned_artifacts=tuple(owned),
        workflow_states=(workflow_scope,),
    )


def load_all_agent_contracts(agents_dir: Path) -> dict[str, AgentContract]:
    """Load all agent markdown contracts as role_id -> AgentContract."""
    if not agents_dir.is_dir():
        raise ParseError(f"{agents_dir}: agents directory not found.")

    result: dict[str, AgentContract] = {}
    for path in sorted(agents_dir.glob("*.md"), key=lambda p: p.name):
        if path.name.lower() == "readme.md":
            continue
        contract = load_agent_contract(path)
        if contract.role_id in result:
            raise ParseError(f"{path}: duplicate role_id '{contract.role_id}'.")
        result[contract.role_id] = contract
    return result


def _extract_artifact_names(section_text: str) -> list[str]:
    # Artifact-like names are explicit file references with well-known extensions.
    names = re.findall(r"`([^`]+\.(?:ya?ml|json|md))`", section_text, flags=re.IGNORECASE)
    return [n.strip() for n in names if n.strip()]


def _slice_section(text: str, heading_prefix: str) -> str:
    start = text.find(heading_prefix)
    if start < 0:
        return ""
    next_h2 = text.find("\n## ", start + len(heading_prefix))
    if next_h2 < 0:
        return text[start:]
    return text[start:next_h2]


def _require_regex(text: str, pattern: str, path: Path, field: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise ParseError(f"{path}: missing required field '{field}'.")
    value = match.group(1).strip()
    if not value:
        raise ParseError(f"{path}: field '{field}' is empty.")
    return value


def _extract_workflow_scope(text: str, path: Path) -> str:
    # Support both documented forms:
    # - **workflow_scope**: `IMPLEMENTING`
    # - **workflow_scope**: all delivery states
    match = re.search(r"\*\*workflow_scope\*\*:\s*(.+)", text)
    if not match:
        raise ParseError(f"{path}: missing required field 'workflow_scope'.")
    raw = match.group(1).strip()
    if raw.startswith("`") and raw.endswith("`") and len(raw) >= 2:
        raw = raw[1:-1].strip()
    if not raw:
        raise ParseError(f"{path}: field 'workflow_scope' is empty.")
    return raw


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Could not read agent contract {path}: {exc}") from exc

