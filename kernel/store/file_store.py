from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


class ParseError(ValueError):
    """Raised when a file cannot be parsed into the expected structured type."""


def atomic_write(path: Path, content: str) -> None:
    """
    Write UTF-8 text atomically with LF line endings and no BOM.
    """
    normalized = _normalize_text(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(normalized, encoding="utf-8", newline="\n")
    tmp.replace(path)


def atomic_rename(src: Path, dst: Path) -> None:
    """
    Atomically rename src to dst. Destination must not already exist.
    """
    if dst.exists():
        raise FileExistsError(f"Destination already exists: {dst}")
    src.replace(dst)


def sha256_from_disk(path: Path) -> str:
    """
    Compute SHA-256 over normalized UTF-8 text with LF newlines.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    normalized = _normalize_text(text).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def read_yaml(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ParseError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError(f"{path}: YAML root must be a mapping.")
    return data


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError(f"{path}: JSON root must be an object.")
    return data


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def append_json_array_element(path: Path, element: dict[str, Any]) -> None:
    """
    Append one object to a JSON array file. Creates file if missing.
    """
    if not path.exists():
        payload: list[dict[str, Any]] = [element]
        atomic_write(path, json.dumps(payload, indent=2))
        return

    text = read_text(path)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON array file {path}: {exc}") from exc
    if not isinstance(data, list):
        raise ParseError(f"{path}: expected a JSON array.")
    data.append(element)
    atomic_write(path, json.dumps(data, indent=2))


def _normalize_text(text: str) -> str:
    # Deterministic line-ending normalization for hashing and writes.
    return text.replace("\r\n", "\n").replace("\r", "\n")

