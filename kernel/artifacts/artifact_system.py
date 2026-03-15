from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kernel.store import file_store
from kernel.types.artifact import ArtifactHash, ArtifactId, ArtifactRef, ArtifactSchema
from kernel.types.run import RunContext


class ArtifactSystemError(RuntimeError):
    """Base class for artifact system errors."""


class MissingArtifactIdError(ArtifactSystemError):
    """Raised when an artifact required to have an ID does not provide one."""


class ArtifactStructureError(ArtifactSystemError):
    """Raised when an artifact fails structural schema validation."""


class ImmutableArtifactError(ArtifactSystemError):
    """Raised when an approved artifact is treated as mutable."""


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class SupersessionResult:
    versioned_path: Path
    prior_artifact_id: ArtifactId
    version_number: int


class ArtifactSystem:
    def register(
        self,
        ctx: RunContext,
        artifact_name: str,
        owner_role: str,
        schemas: dict[str, ArtifactSchema],
    ) -> ArtifactRef:
        """
        Register an artifact that was written to ctx.artifacts_dir.
        """
        _ = owner_role  # role ownership enforcement is handled in invocation layer.
        artifact_path = ctx.artifacts_dir / artifact_name
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        artifact_type = _artifact_type_from_name(artifact_name)
        schema = schemas.get(artifact_type)
        if schema is None:
            raise ArtifactSystemError(f"No schema registered for artifact type '{artifact_type}'.")

        validation = self.validate_structure(artifact_path, schema)
        if not validation.valid:
            raise ArtifactStructureError("; ".join(validation.errors))

        artifact_id = self.read_artifact_field(artifact_path, "id", schema.file_format)
        if "id" in schema.required_fields and not artifact_id:
            raise MissingArtifactIdError(f"{artifact_name}: required field 'id' missing.")

        artifact_hash = self.compute_hash(artifact_path)
        return ArtifactRef(
            name=artifact_name,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
        )

    def validate_structure(
        self,
        artifact_path: Path,
        schema: ArtifactSchema,
    ) -> ValidationResult:
        """
        Validate artifact structure against schema (structural, not semantic).
        """
        errors: list[str] = []
        if not artifact_path.is_file():
            return ValidationResult(valid=False, errors=(f"File not found: {artifact_path}",))
        if artifact_path.stat().st_size == 0:
            return ValidationResult(valid=False, errors=(f"File is empty: {artifact_path}",))

        fmt = schema.file_format.lower()
        if fmt == "markdown":
            errors.extend(self._validate_markdown(artifact_path, schema))
        elif fmt == "yaml":
            errors.extend(self._validate_structured(artifact_path, schema, "yaml"))
        elif fmt == "json":
            errors.extend(self._validate_structured(artifact_path, schema, "json"))
        else:
            errors.append(f"Unsupported schema file_format '{schema.file_format}'.")

        return ValidationResult(valid=len(errors) == 0, errors=tuple(errors))

    def supersede(
        self,
        ctx: RunContext,
        artifact_name: str,
        decision_log_path: Path,
    ) -> SupersessionResult:
        """
        Rename current artifact to the next versioned path: name.v<N>.<ext>.
        """
        artifact_path = ctx.artifacts_dir / artifact_name
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        file_format = _file_format_from_path(artifact_path)
        artifact_id = self.read_artifact_field(artifact_path, "id", file_format)
        if not artifact_id:
            raise MissingArtifactIdError(f"{artifact_name}: cannot supersede without artifact id.")

        if self.check_immutability(artifact_id, decision_log_path):
            raise ImmutableArtifactError(f"Artifact '{artifact_id}' is approved/frozen.")

        version_number = _next_version_number(artifact_path)
        versioned_path = _versioned_path(artifact_path, version_number)
        file_store.atomic_rename(artifact_path, versioned_path)
        return SupersessionResult(
            versioned_path=versioned_path,
            prior_artifact_id=artifact_id,
            version_number=version_number,
        )

    def check_immutability(
        self,
        artifact_id: ArtifactId,
        decision_log_path: Path,
    ) -> bool:
        """
        Return True iff an approve decision references this artifact_id.
        """
        if not decision_log_path.is_file():
            return False
        data = file_store.read_yaml(decision_log_path)
        decisions = data.get("decisions", [])
        if not isinstance(decisions, list):
            return False

        for item in decisions:
            if not isinstance(item, dict):
                continue
            decision = item.get("decision")
            if str(decision).strip().lower() != "approve":
                continue
            references = item.get("references", [])
            if not isinstance(references, list):
                continue
            for ref in references:
                if not isinstance(ref, dict):
                    continue
                if str(ref.get("artifact_id", "")).strip() == artifact_id:
                    return True
        return False

    def compute_hash(self, artifact_path: Path) -> ArtifactHash:
        return file_store.sha256_from_disk(artifact_path)

    def read_artifact_field(
        self,
        artifact_path: Path,
        field_name: str,
        file_format: str,
    ) -> str | None:
        fmt = file_format.lower()
        if fmt == "markdown":
            header = _markdown_header_fields(file_store.read_text(artifact_path))
            value = header.get(field_name)
            return value if value else None
        if fmt == "yaml":
            data = file_store.read_yaml(artifact_path)
            value = data.get(field_name)
            return str(value) if value is not None else None
        if fmt == "json":
            data = file_store.read_json(artifact_path)
            value = data.get(field_name)
            return str(value) if value is not None else None
        return None

    def is_project_input(
        self,
        artifact_path: Path,
        project_root: Path,
    ) -> bool:
        runs_root = (project_root / "runs").resolve()
        path = artifact_path.resolve()
        try:
            path.relative_to(runs_root)
            return False
        except ValueError:
            return True

    def _validate_markdown(self, artifact_path: Path, schema: ArtifactSchema) -> list[str]:
        errors: list[str] = []
        text = file_store.read_text(artifact_path)
        header = _markdown_header_fields(text)
        headings = _markdown_headings(text)

        for field in schema.required_fields:
            value = header.get(field)
            if value is None or not str(value).strip():
                errors.append(f"Missing required markdown header field '{field}'.")

        for required in schema.required_sections:
            required_lower = required.lower()
            if not any(h.lower().startswith(required_lower) for h in headings):
                errors.append(f"Missing required markdown section '{required}'.")

        if "outcome" in schema.required_fields and schema.allowed_outcomes:
            outcome = header.get("outcome")
            allowed = {v for v in schema.allowed_outcomes}
            if outcome not in allowed:
                errors.append(
                    "Invalid outcome value. "
                    f"Expected one of {sorted(allowed)}, got '{outcome}'."
                )
        return errors

    def _validate_structured(
        self,
        artifact_path: Path,
        schema: ArtifactSchema,
        fmt: str,
    ) -> list[str]:
        errors: list[str] = []
        try:
            data = file_store.read_yaml(artifact_path) if fmt == "yaml" else file_store.read_json(artifact_path)
        except file_store.ParseError as exc:
            return [str(exc)]

        nullable_fields = {"supersedes_id", "supersedes_decision_id", "artifact_id", "artifact_hash"}
        for field in schema.required_fields:
            if field not in data:
                errors.append(f"Missing required field '{field}'.")
                continue
            value = data.get(field)
            if value is None and field not in nullable_fields:
                errors.append(f"Required field '{field}' is null.")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"Required field '{field}' is empty.")
            elif isinstance(value, (list, dict)) and len(value) == 0:
                errors.append(f"Required field '{field}' is empty.")
        return errors


def _artifact_type_from_name(artifact_name: str) -> str:
    path = Path(artifact_name)
    suffix = path.suffix
    return path.name[: -len(suffix)] if suffix else path.name


def _file_format_from_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".yaml", ".yml"):
        return "yaml"
    if ext == ".json":
        return "json"
    return "markdown"


def _versioned_path(path: Path, version_number: int) -> Path:
    stem = path.stem
    suffix = path.suffix
    return path.with_name(f"{stem}.v{version_number}{suffix}")


def _next_version_number(path: Path) -> int:
    pattern = re.compile(rf"^{re.escape(path.stem)}\.v(\d+){re.escape(path.suffix)}$")
    max_version = 0
    for candidate in path.parent.iterdir():
        match = pattern.match(candidate.name)
        if match:
            max_version = max(max_version, int(match.group(1)))
    return max_version + 1


def _markdown_header_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = text.splitlines()
    for line in lines:
        if line.startswith("#"):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        k = key.strip()
        v = value.strip()
        if k:
            fields[k] = v
    return fields


def _markdown_headings(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^#{2,3}\s+(.+)$", text, flags=re.MULTILINE)]

