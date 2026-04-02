from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from procwatch.config import AppConfig, SettingsService
from procwatch.database import Database, SystemSample
from procwatch.models import SystemSnapshot
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
        return snapshot

    def recent_samples(self, limit: int = 300) -> list[SystemSample]:
        return self.context.database.recent_system_samples(limit=limit)
