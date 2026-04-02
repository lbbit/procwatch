from datetime import UTC, datetime
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
