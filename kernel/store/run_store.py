from __future__ import annotations

from pathlib import Path

from kernel.types.run import RunId


class RunNotFoundError(FileNotFoundError):
    """Raised when a requested run directory does not exist."""


def create_run_directory(project_root: Path, run_id: RunId) -> Path:
    """
    Create runs/<run_id>/artifacts/ and return runs/<run_id>.

    Raises FileExistsError if the run directory already exists.
    """
    root = project_root / "runs"
    run_dir = root / run_id
    artifacts_dir = run_dir / "artifacts"
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")
    artifacts_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def run_directory(project_root: Path, run_id: RunId) -> Path:
    """Return runs/<run_id> if it exists; otherwise raise RunNotFoundError."""
    run_dir = project_root / "runs" / run_id
    if not run_dir.is_dir():
        raise RunNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def list_run_ids(project_root: Path) -> list[RunId]:
    """Return lexicographically sorted run IDs under runs/."""
    root = project_root / "runs"
    if not root.is_dir():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def decision_log_path(run_dir: Path) -> Path:
    """Return runs/<run_id>/decision_log.yaml path."""
    return run_dir / "decision_log.yaml"


def run_metrics_path(run_dir: Path) -> Path:
    """Return runs/<run_id>/artifacts/run_metrics.json path."""
    return run_dir / "artifacts" / "run_metrics.json"

