from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime.artifacts.artifact_system import ArtifactSystem
from runtime.store import file_store
from runtime.types.artifact import ArtifactSchema
from runtime.types.gate import CheckResult, CheckType, GateCheckDetail, GateResult
from runtime.types.workflow import Transition

# Deterministic mandatory project inputs for input_presence checks.
# Derived from workflow/default_workflow.yaml: inputs.project_mandatory.
REQUIRED_PROJECT_INPUTS: tuple[str, ...] = (
    "domain_scope.md",
    "domain_rules.md",
    "source_policy.md",
    "glossary.md",
    "architecture_contract.md",
)


@dataclass(frozen=True)
class _ApprovalCandidate:
    decision_timestamp: datetime
    reference: dict[str, Any]


class GateEvaluator:
    def __init__(self, artifact_system: ArtifactSystem | None = None) -> None:
        self._artifacts = artifact_system or ArtifactSystem()

    def evaluate(
        self,
        transition: Transition,
        project_root: Path,
        artifacts_dir: Path,
        decision_log_path: Path,
        schemas: dict[str, ArtifactSchema],
    ) -> GateResult:
        checks: list[GateCheckDetail] = []

        # 1) input_presence
        if transition.requires.inputs_present is not None:
            checks.extend(
                self.check_inputs_present(
                    project_root=project_root,
                    required_inputs=list(REQUIRED_PROJECT_INPUTS),
                    expected_presence=transition.requires.inputs_present,
                )
            )

        # 2) artifact_presence
        checks.extend(
            self.check_artifact_presence(
                artifacts_dir=artifacts_dir,
                artifact_names=list(transition.requires.artifacts),
            )
        )

        # 3) approval
        checks.extend(
            self.check_approval(
                artifacts_dir=artifacts_dir,
                decision_log_path=decision_log_path,
                artifact_names=list(transition.requires.human_approval),
                schemas=schemas,
            )
        )

        # 4) condition
        checks.extend(
            self.check_conditions(
                artifacts_dir=artifacts_dir,
                conditions=transition.requires.conditions,
                schemas=schemas,
                decision_log_path=decision_log_path,
            )
        )

        result = CheckResult.PASS if all(c.result == CheckResult.PASS for c in checks) else CheckResult.FAIL
        return GateResult(transition=transition, result=result, checks=tuple(checks))

    def check_inputs_present(
        self,
        project_root: Path,
        required_inputs: list[str],
        expected_presence: bool = True,
    ) -> list[GateCheckDetail]:
        details: list[GateCheckDetail] = []
        for input_name in required_inputs:
            exists = (project_root / input_name).is_file()
            passed = exists if expected_presence else not exists
            detail = None
            if not passed:
                detail = "Expected present." if expected_presence else "Expected absent."
            details.append(
                GateCheckDetail(
                    check_type=CheckType.INPUT_PRESENCE,
                    subject=input_name,
                    result=CheckResult.PASS if passed else CheckResult.FAIL,
                    detail=detail,
                )
            )
        return details

    def check_artifact_presence(
        self,
        artifacts_dir: Path,
        artifact_names: list[str],
    ) -> list[GateCheckDetail]:
        details: list[GateCheckDetail] = []
        for artifact_name in artifact_names:
            exists = (artifacts_dir / artifact_name).is_file()
            details.append(
                GateCheckDetail(
                    check_type=CheckType.ARTIFACT_PRESENCE,
                    subject=artifact_name,
                    result=CheckResult.PASS if exists else CheckResult.FAIL,
                    detail=None if exists else "Artifact file not found.",
                )
            )
        return details

    def check_approval(
        self,
        artifacts_dir: Path,
        decision_log_path: Path,
        artifact_names: list[str],
        schemas: dict[str, ArtifactSchema],
    ) -> list[GateCheckDetail]:
        details: list[GateCheckDetail] = []
        decision_log = self._load_decision_log(decision_log_path)

        for artifact_name in artifact_names:
            artifact_path = artifacts_dir / artifact_name
            if not artifact_path.is_file():
                details.append(
                    GateCheckDetail(
                        check_type=CheckType.APPROVAL,
                        subject=artifact_name,
                        result=CheckResult.FAIL,
                        detail="Artifact not found for approval lookup.",
                    )
                )
                continue

            artifact_type = _artifact_type_from_name(artifact_name)
            schema = schemas.get(artifact_type)
            if schema is None:
                details.append(
                    GateCheckDetail(
                        check_type=CheckType.APPROVAL,
                        subject=artifact_name,
                        result=CheckResult.FAIL,
                        detail=f"No schema registered for artifact type '{artifact_type}'.",
                    )
                )
                continue

            artifact_id = self._artifacts.read_artifact_field(artifact_path, "id", schema.file_format)
            artifact_hash = self._artifacts.compute_hash(artifact_path)
            artifact_created_at = self._artifacts.read_artifact_field(
                artifact_path, "created_at", schema.file_format
            )

            if not artifact_id:
                details.append(
                    GateCheckDetail(
                        check_type=CheckType.APPROVAL,
                        subject=artifact_name,
                        result=CheckResult.FAIL,
                        detail="Artifact id missing; cannot match approval.",
                    )
                )
                continue

            approved = _has_matching_approval(
                decision_log=decision_log,
                artifact_name=artifact_name,
                artifact_id=artifact_id,
                artifact_hash=artifact_hash,
                artifact_created_at=artifact_created_at,
            )
            details.append(
                GateCheckDetail(
                    check_type=CheckType.APPROVAL,
                    subject=artifact_name,
                    result=CheckResult.PASS if approved else CheckResult.FAIL,
                    detail=None if approved else "No matching approval entry found.",
                )
            )
        return details

    def check_conditions(
        self,
        artifacts_dir: Path,
        conditions: dict[str, str],
        schemas: dict[str, ArtifactSchema],
        decision_log_path: Path | None = None,
    ) -> list[GateCheckDetail]:
        details: list[GateCheckDetail] = []
        for field_name, expected_value in conditions.items():
            if field_name == "note":
                # Workflow authors may include a human-readable note under conditions.
                # It is explicit metadata, not a gate predicate.
                continue
            if field_name == "decision_log_reject_for":
                details.append(
                    self._check_decision_log_reject_for(
                        artifacts_dir=artifacts_dir,
                        decision_log_path=decision_log_path,
                        artifact_name=expected_value,
                        schemas=schemas,
                    )
                )
                continue
            matches: list[tuple[str, str]] = []
            for artifact_path in sorted(artifacts_dir.iterdir(), key=lambda p: p.name):
                if not artifact_path.is_file():
                    continue
                artifact_name = artifact_path.name
                artifact_type = _artifact_type_from_name(artifact_name)
                schema = schemas.get(artifact_type)
                if schema is None:
                    continue

                value = self._artifacts.read_artifact_field(artifact_path, field_name, schema.file_format)
                if value is None and field_name.endswith("_outcome"):
                    # Explicit deterministic mapping: <prefix>_outcome can read 'outcome'
                    # from artifacts whose type starts with the same prefix.
                    prefix = field_name[: -len("_outcome")]
                    if artifact_type.startswith(prefix):
                        value = self._artifacts.read_artifact_field(
                            artifact_path, "outcome", schema.file_format
                        )
                if value is not None:
                    matches.append((artifact_name, value))

            if len(matches) == 0:
                details.append(
                    GateCheckDetail(
                        check_type=CheckType.CONDITION,
                        subject=field_name,
                        result=CheckResult.FAIL,
                        detail=f"No artifact field found for condition '{field_name}'.",
                    )
                )
                continue
            if len(matches) > 1:
                details.append(
                    GateCheckDetail(
                        check_type=CheckType.CONDITION,
                        subject=field_name,
                        result=CheckResult.FAIL,
                        detail=f"Ambiguous condition source across artifacts: {[m[0] for m in matches]}",
                    )
                )
                continue

            artifact_name, actual = matches[0]
            passed = actual == expected_value  # exact, case-sensitive comparison.
            details.append(
                GateCheckDetail(
                    check_type=CheckType.CONDITION,
                    subject=field_name,
                    result=CheckResult.PASS if passed else CheckResult.FAIL,
                    detail=None
                    if passed
                    else f"{artifact_name}: expected '{expected_value}', got '{actual}'.",
                )
            )
        return details

    def _check_decision_log_reject_for(
        self,
        artifacts_dir: Path,
        decision_log_path: Path | None,
        artifact_name: str,
        schemas: dict[str, ArtifactSchema],
    ) -> GateCheckDetail:
        if decision_log_path is None:
            return GateCheckDetail(
                check_type=CheckType.CONDITION,
                subject="decision_log_reject_for",
                result=CheckResult.FAIL,
                detail="decision_log_path is required for decision_log_reject_for.",
            )
        decision_log = self._load_decision_log(decision_log_path)
        decisions = decision_log.get("decisions", [])
        if not isinstance(decisions, list):
            return GateCheckDetail(
                check_type=CheckType.CONDITION,
                subject="decision_log_reject_for",
                result=CheckResult.FAIL,
                detail="decision_log.yaml has invalid decisions payload.",
            )

        artifact_id: str | None = None
        artifact_path = artifacts_dir / artifact_name
        if artifact_path.is_file():
            artifact_type = _artifact_type_from_name(artifact_name)
            schema = schemas.get(artifact_type)
            if schema is not None:
                artifact_id = self._artifacts.read_artifact_field(artifact_path, "id", schema.file_format)

        for entry in decisions:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("decision", "")).strip().lower() != "reject":
                continue
            references = entry.get("references", [])
            if not isinstance(references, list):
                continue
            for ref in references:
                if not isinstance(ref, dict):
                    continue
                ref_artifact = str(ref.get("artifact", "")).strip()
                ref_artifact_id = str(ref.get("artifact_id", "")).strip()
                if ref_artifact == artifact_name:
                    return GateCheckDetail(
                        check_type=CheckType.CONDITION,
                        subject="decision_log_reject_for",
                        result=CheckResult.PASS,
                        detail=None,
                    )
                if artifact_id and ref_artifact_id == artifact_id:
                    return GateCheckDetail(
                        check_type=CheckType.CONDITION,
                        subject="decision_log_reject_for",
                        result=CheckResult.PASS,
                        detail=None,
                    )

        return GateCheckDetail(
            check_type=CheckType.CONDITION,
            subject="decision_log_reject_for",
            result=CheckResult.FAIL,
            detail=f"No reject decision found for '{artifact_name}'.",
        )

    @staticmethod
    def _load_decision_log(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {"decisions": []}
        try:
            return file_store.read_yaml(path)
        except file_store.ParseError:
            return {"decisions": []}


def _artifact_type_from_name(artifact_name: str) -> str:
    path = Path(artifact_name)
    stem = path.stem
    # Strip deterministic version suffix ".v<N>" from stem if present.
    if ".v" in stem:
        head, tail = stem.rsplit(".v", 1)
        if tail.isdigit():
            stem = head
    return stem


def _has_matching_approval(
    decision_log: dict[str, Any],
    artifact_name: str,
    artifact_id: str,
    artifact_hash: str,
    artifact_created_at: str | None,
) -> bool:
    decisions = decision_log.get("decisions", [])
    if not isinstance(decisions, list):
        return False

    created_at_dt = _parse_iso8601(artifact_created_at) if artifact_created_at else None

    candidates: list[_ApprovalCandidate] = []
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("decision", "")).strip().lower() != "approve":
            continue
        timestamp = _parse_iso8601(entry.get("timestamp"))
        if timestamp is None:
            continue
        references = entry.get("references", [])
        if not isinstance(references, list):
            continue
        for ref in references:
            if not isinstance(ref, dict):
                continue
            ref_artifact = str(ref.get("artifact", "")).strip()
            ref_id = str(ref.get("artifact_id", "")).strip()
            ref_hash = str(ref.get("artifact_hash", "")).strip()

            if ref_artifact and ref_artifact != artifact_name:
                continue
            if ref_id != artifact_id:
                continue
            if ref_hash and ref_hash != artifact_hash:
                continue
            candidates.append(_ApprovalCandidate(decision_timestamp=timestamp, reference=ref))

    if not candidates:
        return False

    if created_at_dt is None:
        return True
    return any(c.decision_timestamp > created_at_dt for c in candidates)


def _parse_iso8601(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

