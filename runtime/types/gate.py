from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from runtime.types.workflow import Transition


class CheckType(str, Enum):
    INPUT_PRESENCE = "input_presence"
    ARTIFACT_PRESENCE = "artifact_presence"
    APPROVAL = "approval"
    CONDITION = "condition"


class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class GateCheckDetail:
    check_type: CheckType
    subject: str
    result: CheckResult
    detail: str | None


@dataclass(frozen=True)
class GateResult:
    transition: Transition
    result: CheckResult
    checks: tuple[GateCheckDetail, ...]

