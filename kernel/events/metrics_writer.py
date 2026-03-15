from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kernel.store.file_store import atomic_write, sha256_from_disk


class EventCounterViolationError(RuntimeError):
    """Raised when a non-monotonic event counter is detected."""


class AppendOnlyViolationError(RuntimeError):
    """Raised when run_metrics content is not append-only relative to prior snapshot."""


def append_event(
    run_metrics_path: Path,
    event_dict: dict[str, Any],
    section: str,
) -> None:
    """
    Append one event dict to run_metrics.json in the given section.
    """
    if section not in {"events", "invocation_records"}:
        raise ValueError("section must be 'events' or 'invocation_records'.")

    data = _load_or_init(run_metrics_path)
    existing = data.get(section, [])
    if not isinstance(existing, list):
        raise ValueError(f"run_metrics section '{section}' must be an array.")

    _verify_monotonic_counter(existing, event_dict)
    existing.append(event_dict)
    data[section] = existing
    atomic_write(run_metrics_path, json.dumps(data, indent=2))


def verify_append_only(run_metrics_path: Path, prior_hash: str) -> None:
    """
    Verify run_metrics remains append-only relative to recorded snapshot.
    """
    if not run_metrics_path.is_file():
        raise AppendOnlyViolationError(f"run_metrics file missing: {run_metrics_path}")

    snapshot = _snapshot_path(run_metrics_path, prior_hash)
    if not snapshot.is_file():
        raise AppendOnlyViolationError(
            f"Missing prior snapshot for hash {prior_hash}; cannot verify append-only."
        )

    prior_text = snapshot.read_text(encoding="utf-8")
    current_text = run_metrics_path.read_text(encoding="utf-8")
    if not current_text.startswith(prior_text):
        raise AppendOnlyViolationError("run_metrics content is not append-only.")


def _load_or_init(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "run_metadata": {},
            "events": [],
            "invocation_records": [],
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("run_metrics root must be an object.")
    payload.setdefault("run_metadata", {})
    payload.setdefault("events", [])
    payload.setdefault("invocation_records", [])
    return payload


def _verify_monotonic_counter(existing: list[Any], incoming: dict[str, Any]) -> None:
    incoming_id = str(incoming.get("event_id", "")).strip()
    incoming_counter = _event_counter(incoming_id)
    if incoming_counter is None:
        return

    max_existing = -1
    for item in existing:
        if not isinstance(item, dict):
            continue
        counter = _event_counter(str(item.get("event_id", "")))
        if counter is not None:
            max_existing = max(max_existing, counter)
    if incoming_counter <= max_existing:
        raise EventCounterViolationError(
            f"Incoming event counter {incoming_counter} is not greater than existing {max_existing}."
        )


def _event_counter(event_id: str) -> int | None:
    # Expected format EVT-<run-short>-<counter>
    parts = event_id.split("-")
    if len(parts) < 3:
        return None
    tail = parts[-1]
    if not tail.isdigit():
        return None
    return int(tail)


def file_hash(path: Path) -> str:
    """
    Return deterministic file hash and persist a snapshot for append-only verification.
    """
    digest = sha256_from_disk(path)
    snapshot = _snapshot_path(path, digest)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return digest


def _snapshot_path(path: Path, digest: str) -> Path:
    return path.parent / ".append_only_snapshots" / f"{path.name}.{digest}.snapshot"

