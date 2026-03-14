from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ArtifactId = str
ArtifactHash = str


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    artifact_id: ArtifactId | None
    artifact_hash: ArtifactHash | None


class ArtifactStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ArtifactSchema:
    artifact_type: str
    file_format: str
    required_fields: tuple[str, ...]
    required_sections: tuple[str, ...]
    allowed_outcomes: tuple[str, ...] | None
    owner_roles: tuple[str, ...]

