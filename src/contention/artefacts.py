"""The git-ignored `artefacts/` directory: derived files, one directory per refresh run.

Trained models, batch input and output files, detailed eval outputs and logs are
derived from API Data, so each lives in the directory of the run that made it and
is deleted with that run once it is older than the retention period.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from contention.collect import RETENTION

_RUN_NAME = "run-%Y%m%dT%H%M%SZ"


def run_dir(root: Path, started_at: datetime) -> Path:
    """Create and return the directory for the refresh run that started at `started_at`."""
    path = root / started_at.astimezone(UTC).strftime(_RUN_NAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


def purge_runs(root: Path, now: datetime) -> list[str]:
    """Delete runs older than the retention period; return their names.

    A run is a run directory, or a file named after one with a suffix, such as
    `run-20260927T030000Z.launchd.log`. Anything else in `root` is left alone.
    """
    if not root.is_dir():
        return []
    deleted = []
    for path in sorted(root.iterdir()):
        try:
            started_at = datetime.strptime(path.name.split(".")[0], _RUN_NAME).replace(tzinfo=UTC)
        except ValueError:
            continue
        if started_at < now - RETENTION:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
            deleted.append(path.name)
    return deleted
