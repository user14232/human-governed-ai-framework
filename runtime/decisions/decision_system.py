from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.events.event_system import EventSystem
from runtime.store import file_store
from runtime.store.run_store import run_metrics_path
from runtime.types.artifact import ArtifactHash, ArtifactId, ArtifactRef, ArtifactSchema
from runtime.types.decision import DecisionEntry, DecisionReference, DecisionType
from runtime.types.event import EventType
from runtime.types.run import RunContext


class DecisionLogParseError(ValueError):
    """Raised when decision_log.yaml is malformed."""


class SignalType(str, Enum):
    GATE_RECHECK = "gate_recheck"
    REWORK = "rework"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class DecisionSignal:
    signal_type: SignalType
    entry: DecisionEntry
    artifact_ref: ArtifactRef | None


class DecisionSystem:
    def __init__(self, event_system: EventSystem | None = None) -> None:
        self._events = event_system

    def load_all(self, decision_log_path: Path) -> list[DecisionEntry]:
        if not decision_log_path.is_file():
            return []
        try:
            payload = file_store.read_yaml(decision_log_path)
        except file_store.ParseError as exc:
            raise DecisionLogParseError(str(exc)) from exc

        schema_version = payload.get("schema_version")
        if schema_version != "v1":
            raise DecisionLogParseError("decision_log.yaml must declare schema_version: v1.")

        raw_decisions = payload.get("decisions")
        if not isinstance(raw_decisions, list):
            raise DecisionLogParseError("decision_log.yaml field 'decisions' must be a list.")

        result: list[DecisionEntry] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(raw_decisions):
            entry = self._parse_entry(item, index)
            if entry.decision_id in seen_ids:
                raise DecisionLogParseError(f"Duplicate decision_id '{entry.decision_id}' in decision log.")
            seen_ids.add(entry.decision_id)
            result.append(entry)
        return result

    def get_new_entries(self, decision_log_path: Path, last_known_count: int) -> list[DecisionEntry]:
        if last_known_count < 0:
            raise ValueError("last_known_count must be >= 0.")
        entries = self.load_all(decision_log_path)
        if last_known_count >= len(entries):
            return []
        return entries[last_known_count:]

    def process_new_entries(
        self,
        ctx: RunContext,
        decision_log_path: Path,
        last_known_count: int,
        schemas: dict[str, ArtifactSchema],
    ) -> list[DecisionSignal]:
        _ = schemas  # schema-dependent content checks are out of scope for decision parsing.
        new_entries = self.get_new_entries(decision_log_path, last_known_count)
        signals: list[DecisionSignal] = []

        for entry in new_entries:
            if self._events is not None:
                self._events.emit(
                    run_metrics_path=run_metrics_path(ctx.run_dir),
                    run_id=ctx.run_id,
                    event_type=EventType.DECISION_RECORDED,
                    producer="human",
                    workflow_state=ctx.current_state,
                    causation_event_id=None,
                    payload={
                        "decision_id": entry.decision_id,
                        "decision": entry.decision.value,
                        "scope": entry.scope,
                        "reference_count": len(entry.references),
                    },
                )
            signals.append(self._signal_from_entry(entry))
        return signals

    def find_approval(
        self,
        entries: list[DecisionEntry],
        artifact_id: ArtifactId,
        artifact_hash: ArtifactHash | None,
        artifact_created_at: str,
    ) -> DecisionEntry | None:
        created_at = _parse_iso8601(artifact_created_at)
        if created_at is None:
            return None

        for entry in entries:
            if entry.decision is not DecisionType.APPROVE:
                continue
            decision_ts = _parse_iso8601(entry.timestamp)
            if decision_ts is None or decision_ts <= created_at:
                continue
            for ref in entry.references:
                if ref.artifact_id != artifact_id:
                    continue
                if artifact_hash is not None and ref.artifact_hash != artifact_hash:
                    continue
                return entry
        return None

    def _signal_from_entry(self, entry: DecisionEntry) -> DecisionSignal:
        if entry.decision is DecisionType.APPROVE:
            return DecisionSignal(signal_type=SignalType.GATE_RECHECK, entry=entry, artifact_ref=None)
        if entry.decision is DecisionType.DEFER:
            return DecisionSignal(signal_type=SignalType.DEFERRED, entry=entry, artifact_ref=None)
        # reject -> deterministic rework signal, preferring first declared reference.
        ref = entry.references[0] if entry.references else None
        artifact_ref = (
            ArtifactRef(name=ref.artifact, artifact_id=ref.artifact_id, artifact_hash=ref.artifact_hash)
            if ref is not None
            else None
        )
        return DecisionSignal(signal_type=SignalType.REWORK, entry=entry, artifact_ref=artifact_ref)

    def _parse_entry(self, raw: Any, index: int) -> DecisionEntry:
        if not isinstance(raw, dict):
            raise DecisionLogParseError(f"Decision entry at index {index} must be an object.")

        decision_id = _required_non_empty_str(raw, "decision_id", index)
        timestamp = _required_iso8601(raw, "timestamp", index)
        actor = _required_non_empty_str(raw, "human_identity", index)
        scope = _required_non_empty_str(raw, "scope", index)
        decision_raw = _required_non_empty_str(raw, "decision", index).lower()
        try:
            decision = DecisionType(decision_raw)
        except ValueError as exc:
            raise DecisionLogParseError(
                f"Decision entry at index {index} has invalid decision '{decision_raw}'."
            ) from exc

        references_raw = raw.get("references")
        if not isinstance(references_raw, list):
            raise DecisionLogParseError(f"Decision entry at index {index} field 'references' must be a list.")
        references: list[DecisionReference] = []
        for ref_index, ref in enumerate(references_raw):
            references.append(_parse_reference(ref, index, ref_index))

        return DecisionEntry(
            decision_id=decision_id,
            decision=decision,
            scope=scope,
            timestamp=timestamp,
            actor=actor,
            references=tuple(references),
        )


def _parse_reference(raw: Any, decision_index: int, ref_index: int) -> DecisionReference:
    if not isinstance(raw, dict):
        raise DecisionLogParseError(
            f"Decision entry at index {decision_index} reference {ref_index} must be an object."
        )
    artifact = _required_non_empty_str(raw, "artifact", decision_index)
    artifact_id = _optional_str_or_none(raw, "artifact_id", decision_index)
    artifact_hash = _optional_str_or_none(raw, "artifact_hash", decision_index)
    return DecisionReference(artifact=artifact, artifact_id=artifact_id, artifact_hash=artifact_hash)


def _required_non_empty_str(raw: dict[str, Any], key: str, index: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DecisionLogParseError(f"Decision entry at index {index} field '{key}' must be a non-empty string.")
    return value.strip()


def _required_iso8601(raw: dict[str, Any], key: str, index: int) -> str:
    value = _required_non_empty_str(raw, key, index)
    if _parse_iso8601(value) is None:
        raise DecisionLogParseError(
            f"Decision entry at index {index} field '{key}' must be a valid ISO-8601 timestamp."
        )
    return value


def _optional_str_or_none(raw: dict[str, Any], key: str, index: int) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    raise DecisionLogParseError(f"Decision entry at index {index} field '{key}' must be a string or null.")


def _parse_iso8601(raw: str) -> datetime | None:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

