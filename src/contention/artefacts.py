"""The git-ignored `artefacts/` directory: derived files, one directory per refresh run.

Trained models, batch input and output files, detailed eval outputs and logs are
derived from API Data, so each lives in the directory of the run that made it and
is deleted with that run once it is older than the retention period.
"""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

RETENTION = timedelta(days=28)  # API Data, and anything derived from it, is kept at most this long
_RUN_NAME = "run-%Y%m%dT%H%M%SZ"


def run_dir(root: Path, started_at: datetime) -> Path:
    """Create and return the directory for the refresh run that started at `started_at`."""
    path = Path(root) / started_at.astimezone(UTC).strftime(_RUN_NAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


def purge_runs(root: Path, now: datetime) -> list[str]:
    """Delete run directories older than the retention period; return their names.

    Anything in `root` that isn't a run directory is left alone.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    deleted = []
    for path in sorted(root.iterdir()):
        try:
            started_at = datetime.strptime(path.name, _RUN_NAME).replace(tzinfo=UTC)
        except ValueError:
            continue
        if path.is_dir() and started_at < now - RETENTION:
            shutil.rmtree(path)
            deleted.append(path.name)
    return deleted
