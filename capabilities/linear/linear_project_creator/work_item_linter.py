"""
Backward-compatible linter alias.
"""

from capabilities.planning.work_item_linter import LintViolation, lint_project

__all__ = ["LintViolation", "lint_project"]

