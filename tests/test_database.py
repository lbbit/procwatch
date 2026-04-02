from datetime import UTC, datetime, timedelta
from pathlib import Path

from procwatch.database import Database
from procwatch.models import ProcessMetric, SystemSnapshot


def test_insert_and_query_snapshot(tmp_path: Path) -> None:
    db = Database(tmp_path / "procwatch.sqlite3")
    db.create_schema()
    snapshot = SystemSnapshot(
        timestamp=datetime.now(UTC),
        cpu_percent=12.5,
        memory_percent=48.3,
        total_memory_mb=16000,
        used_memory_mb=7700,
        top_cpu_processes=[
            ProcessMetric(pid=1, process_name="a", cpu_percent=10.0, memory_mb=20.0)
        ],
        top_memory_processes=[
            ProcessMetric(pid=2, process_name="b", cpu_percent=2.0, memory_mb=120.0)
        ],
    )
    db.insert_snapshot(snapshot)
    rows = db.recent_system_samples()
    assert len(rows) == 1
    assert rows[0].cpu_percent == 12.5
    history = db.history_points()
    assert len(history) == 1
    assert history[0].sample_id == rows[0].id
    cpu_rows = db.processes_for_sample(rows[0].id, "cpu")
    assert cpu_rows[0].process_name == "a"


def test_purge_old_snapshots(tmp_path: Path) -> None:
    db = Database(tmp_path / "procwatch.sqlite3")
    db.create_schema()
    old_snapshot = SystemSnapshot(
        timestamp=datetime.now(UTC) - timedelta(days=40),
        cpu_percent=1.0,
        memory_percent=10.0,
        total_memory_mb=16000,
        used_memory_mb=1000,
        top_cpu_processes=[],
        top_memory_processes=[],
    )
    new_snapshot = SystemSnapshot(
        timestamp=datetime.now(UTC),
        cpu_percent=2.0,
        memory_percent=20.0,
        total_memory_mb=16000,
        used_memory_mb=2000,
        top_cpu_processes=[],
        top_memory_processes=[],
    )
    db.insert_snapshot(old_snapshot)
    db.insert_snapshot(new_snapshot)
    db.purge_older_than(datetime.now(UTC) - timedelta(days=30))
    rows = db.recent_system_samples(limit=10)
    assert len(rows) == 1
    assert rows[0].cpu_percent == 2.0
