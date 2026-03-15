"""
Backward-compatible planning engine alias.
"""

from capabilities.planning.planning_engine import (  # noqa: F401
    DEFAULT_PROJECT_PLAN_PATH,
    PlanValidationError,
    PlanningEngine,
    PlanningValidationResult,
)

__all__ = [
    "DEFAULT_PROJECT_PLAN_PATH",
    "PlanValidationError",
    "PlanningEngine",
    "PlanningValidationResult",
]

