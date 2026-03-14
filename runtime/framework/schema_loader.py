from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from runtime.types.artifact import ArtifactSchema


class ParseError(ValueError):
    """Raised when an artifact schema cannot be parsed deterministically."""


def load_schema(schema_path: Path) -> ArtifactSchema:
    """
    Parse one artifact schema file and return a typed ArtifactSchema.

    Supported schema files:
    - YAML/JSON contract files with keys like schema_id, artifact_name, required_fields
    - Markdown schema docs under artifacts/schemas/*.schema.md
    """
    suffixes = [s.lower() for s in schema_path.suffixes]
    if suffixes[-2:] == [".schema", ".md"]:
        return _load_markdown_schema(schema_path)
    if suffixes[-2:] in ([ ".schema", ".yaml"], [".schema", ".yml"]):
        return _load_structured_schema(schema_path, "yaml")
    if suffixes[-2:] == [".schema", ".json"]:
        return _load_structured_schema(schema_path, "json")
    raise ParseError(
        f"{schema_path}: unsupported schema extension. Expected *.schema.yaml|yml|json|md."
    )


def load_all_schemas(schemas_dir: Path) -> dict[str, ArtifactSchema]:
    """Load all schemas from a directory as artifact_type -> ArtifactSchema."""
    if not schemas_dir.is_dir():
        raise ParseError(f"{schemas_dir}: schemas directory not found.")

    result: dict[str, ArtifactSchema] = {}
    patterns = ("*.schema.yaml", "*.schema.yml", "*.schema.json", "*.schema.md")
    for pattern in patterns:
        for path in sorted(schemas_dir.glob(pattern), key=lambda p: p.name):
            schema = load_schema(path)
            if schema.artifact_type in result:
                raise ParseError(
                    f"{schemas_dir}: duplicate artifact_type '{schema.artifact_type}' in {path.name}."
                )
            result[schema.artifact_type] = schema
    return result


def _load_structured_schema(path: Path, loader: str) -> ArtifactSchema:
    data = _read_mapping(path, loader)
    artifact_type = _first_str(data, ("schema_id", "artifact_type"), path) or _infer_type_from_filename(path)
    artifact_name = _first_str(data, ("artifact_name",), path)
    file_format = _artifact_format_from_name(artifact_name)
    required_fields = _extract_required_fields(data.get("required_fields"))
    owner_roles = tuple(_as_str_list(data.get("owner_roles"), path, "owner_roles"))
    allowed_outcomes = _extract_allowed_outcomes(data.get("allowed_outcomes"))
    return ArtifactSchema(
        artifact_type=artifact_type,
        file_format=file_format,
        required_fields=required_fields,
        required_sections=tuple(),
        allowed_outcomes=allowed_outcomes,
        owner_roles=owner_roles,
    )


def _load_markdown_schema(path: Path) -> ArtifactSchema:
    text = _read_text(path)
    artifact_type = _capture_inline_code(text, r"\*\*schema_id\*\*:\s*`([^`]+)`")
    artifact_name = _capture_inline_code(text, r"\*\*artifact_name\*\*:\s*`([^`]+)`")

    required_fields = tuple(
        sorted(
            {
                m.group(1).strip()
                for m in re.finditer(
                    r"^\s*-\s*`([^`]+)`\s*:",
                    _slice_markdown_section(text, "## Required artifact fields"),
                    flags=re.MULTILINE,
                )
            }
        )
    )
    required_sections = tuple(
        _extract_required_section_headings(_slice_markdown_section(text, "## Required sections"))
    )
    owner_roles = tuple(
        sorted(
            {
                m.group(1).strip()
                for m in re.finditer(
                    r"^\s*-\s*`([^`]+)`\s*$",
                    _slice_markdown_section(text, "## Owner roles"),
                    flags=re.MULTILINE,
                )
            }
        )
    )
    allowed_outcomes = _extract_allowed_outcomes_from_markdown(text)

    return ArtifactSchema(
        artifact_type=artifact_type or _infer_type_from_filename(path),
        file_format=_artifact_format_from_name(artifact_name),
        required_fields=required_fields,
        required_sections=required_sections,
        allowed_outcomes=allowed_outcomes,
        owner_roles=owner_roles,
    )


def _read_mapping(path: Path, loader: str) -> dict[str, Any]:
    text = _read_text(path)
    try:
        if loader == "yaml":
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"{path}: parse error ({loader}): {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError(f"{path}: top-level schema must be a mapping.")
    return data


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParseError(f"Could not read schema file {path}: {exc}") from exc


def _first_str(data: dict[str, Any], keys: tuple[str, ...], path: Path) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ParseError(f"{path}: field '{key}' must be a non-empty string.")
        return value.strip()
    return None


def _extract_required_fields(value: Any) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if not isinstance(value, list):
        return tuple()
    fields: list[str] = []
    for item in value:
        if isinstance(item, str):
            fields.append(item.strip())
        elif isinstance(item, dict):
            for key in item.keys():
                if isinstance(key, str):
                    fields.append(key.strip())
    return tuple(sorted({f for f in fields if f}))


def _extract_allowed_outcomes(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, list):
        outcomes = tuple(sorted({str(v).strip() for v in value if str(v).strip()}))
        return outcomes or None
    return None


def _extract_allowed_outcomes_from_markdown(text: str) -> tuple[str, ...] | None:
    # Keep this explicit and deterministic: only parse upper-case, underscore tokens.
    section = _slice_markdown_section(text, "## Required artifact fields")
    tokens = re.findall(r"`([A-Z][A-Z0-9_]+)`", section)
    if not tokens:
        return None
    return tuple(sorted(set(tokens)))


def _capture_inline_code(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _slice_markdown_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    next_heading = text.find("\n## ", start + len(heading))
    if next_heading < 0:
        return text[start:]
    return text[start:next_heading]


def _extract_required_section_headings(section_text: str) -> tuple[str, ...]:
    headings: list[str] = []
    for raw in re.findall(r"^###\s+(.+)$", section_text, flags=re.MULTILINE):
        heading = raw.strip()
        heading = re.sub(r"^\d+\)\s*", "", heading)
        if heading:
            headings.append(heading)
    return tuple(headings)


def _artifact_format_from_name(artifact_name: str | None) -> str:
    if not artifact_name:
        return "unknown"
    ext = Path(artifact_name).suffix.lower().lstrip(".")
    if ext in {"yaml", "yml"}:
        return "yaml"
    if ext in {"json"}:
        return "json"
    if ext in {"md", "markdown"}:
        return "markdown"
    return ext or "unknown"


def _infer_type_from_filename(path: Path) -> str:
    name = path.name
    for suffix in (".schema.yaml", ".schema.yml", ".schema.json", ".schema.md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _as_str_list(value: Any, path: Path, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ParseError(f"{path}: field '{field}' must be a list of strings.")
    result: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ParseError(f"{path}: field '{field}[{idx}]' must be a non-empty string.")
        result.append(item.strip())
    return result

