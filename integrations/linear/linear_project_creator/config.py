"""
Runtime configuration loaded exclusively from environment variables.

Raises ValueError with an explicit message for every missing required variable.
No defaults are substituted silently.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    team_id: str
    api_url: str


LINEAR_API_URL = "https://api.linear.app/graphql"


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Required:
        LINEAR_API_KEY  — Personal or application API key for Linear.
        LINEAR_TEAM_ID  — Linear team identifier (UUID).

    Raises:
        ValueError: If any required variable is absent.
    """
    load_dotenv()

    missing: list[str] = []

    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        missing.append("LINEAR_API_KEY")

    team_id = os.environ.get("LINEAR_TEAM_ID", "")
    if not team_id:
        missing.append("LINEAR_TEAM_ID")

    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Set them before running this tool."
        )

    return Config(
        api_key=api_key,
        team_id=team_id,
        api_url=LINEAR_API_URL,
    )
