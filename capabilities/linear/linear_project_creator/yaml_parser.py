"""
Backward-compatible parser alias.
"""

from capabilities.planning.planning_parser import parse_planning_yaml as parse_yaml

__all__ = ["parse_yaml"]

