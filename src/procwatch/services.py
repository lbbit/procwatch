from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from procwatch.config import AppConfig, SettingsService
from procwatch.database import Database, HistoryPoint, SystemSample
from procwatch.models import ProcessMetric, SystemSnapshot
from procwatch.monitor import SystemSampler


@dataclass
class AppContext:
    config: AppConfig
    settings_service: SettingsService
    database: Database
    sampler: SystemSampler


def create_app_context(base_dir: Path) -> AppContext:
    config_path = base_dir / "runtime" / "config.json"
    settings_service = SettingsService(config_path)
    config = settings_service.load()
    database = Database(base_dir / config.monitor.database_path)
    database.create_schema()
    sampler = SystemSampler()
    return AppContext(
        config=config,
        settings_service=settings_service,
        database=database,
        sampler=sampler,
    )


class MonitorService:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    def collect_once(self) -> SystemSnapshot:
        snapshot = self.context.sampler.sample(
            top_n_cpu=self.context.config.monitor.top_n_cpu,
            top_n_memory=self.context.config.monitor.top_n_memory,
        )
        self.context.database.insert_snapshot(snapshot)
        self._purge_history_if_needed()
        return snapshot

    def recent_samples(self, limit: int = 300) -> list[SystemSample]:
        return self.context.database.recent_system_samples(limit=limit)

    def history_points(self, limit: int = 2000) -> list[HistoryPoint]:
        return self.context.database.history_points(limit=limit)

    def sample_processes(self, sample_id: int, category: str) -> list[ProcessMetric]:
        return self.context.database.processes_for_sample(sample_id=sample_id, category=category)

    def _purge_history_if_needed(self) -> None:
        retention_days = self.context.config.monitor.retention_days
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        self.context.database.purge_older_than(cutoff)
