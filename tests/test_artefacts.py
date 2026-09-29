from datetime import UTC, datetime, timedelta

from contention.artefacts import purge_runs, run_dir

NOW = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)


def test_a_run_gets_its_own_directory_tagged_with_when_it_started(tmp_path):
    path = run_dir(tmp_path, NOW)

    assert path == tmp_path / "run-20260927T030000Z"
    assert path.is_dir()


def test_deletes_runs_older_than_28_days_and_keeps_the_rest(tmp_path):
    old = run_dir(tmp_path, NOW - timedelta(days=28, seconds=1))
    (old / "batch-output.jsonl").write_text("{}")
    (old / "models").mkdir()
    (old / "models" / "predictor.txt").write_text("trees")
    edge = run_dir(tmp_path, NOW - timedelta(days=28))
    recent = run_dir(tmp_path, NOW - timedelta(days=7))
    old_log = tmp_path / f"{old.name}.launchd.log"
    old_log.write_text("refreshed")
    unrelated = tmp_path / "notes.txt"
    unrelated.write_text("not a run")

    deleted = purge_runs(tmp_path, NOW)

    assert deleted == [old.name, old_log.name]
    assert not old.exists() and not old_log.exists()
    assert edge.exists() and recent.exists() and unrelated.exists()


def test_a_missing_artefacts_directory_is_nothing_to_purge(tmp_path):
    assert purge_runs(tmp_path / "artefacts", NOW) == []
