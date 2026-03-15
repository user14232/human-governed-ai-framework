"""
Linear integration entrypoint.

Delegates to the DevOS planning CLI sync command.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.planning.cli import main as planning_main


def main(argv: list[str] | None = None) -> int:
    args = [] if argv is None else list(argv)
    if not args:
        args = ["sync", "linear"]
    elif args[0] not in {"sync", "validate"}:
        args = ["sync", "linear", *args]
    return planning_main(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

