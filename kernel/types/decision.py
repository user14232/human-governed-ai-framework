from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kernel.types.artifact import ArtifactHash, ArtifactId


class DecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


@dataclass(frozen=True)
class DecisionReference:
    artifact: str
    artifact_id: ArtifactId | None
    artifact_hash: ArtifactHash | None


@dataclass(frozen=True)
class DecisionEntry:
    decision_id: str
    decision: DecisionType
    scope: str
    timestamp: str
    actor: str
    references: tuple[DecisionReference, ...]

