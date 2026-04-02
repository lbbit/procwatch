from __future__ import annotations

import configparser
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class MonitorSettings(BaseModel):
    sampling_interval_seconds: float = Field(default=2.0, ge=1.0, le=60.0)
    top_n_cpu: int = Field(default=8, ge=1, le=50)
    top_n_memory: int = Field(default=8, ge=1, le=50)
    retention_days: int = Field(default=30, ge=1, le=3650)
    start_minimized: bool = False
    close_to_tray: bool = True
    enable_tray: bool = True
    auto_start: bool = False
    theme: Literal["dark", "light"] = "dark"
    database_path: str = "runtime/procwatch.sqlite3"


class AppConfig(BaseModel):
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)


DEFAULT_CONFIG = AppConfig()


class SettingsService:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            return DEFAULT_CONFIG.model_copy(deep=True)
        return AppConfig.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    def export_json(self, config: AppConfig, target: Path) -> None:
        target.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    def import_json(self, source: Path) -> AppConfig:
        return AppConfig.model_validate_json(source.read_text(encoding="utf-8"))

    def export_ini(self, config: AppConfig, target: Path) -> None:
        parser = configparser.ConfigParser()
        parser["monitor"] = {
            key: json.dumps(value) if isinstance(value, bool) else str(value)
            for key, value in config.monitor.model_dump().items()
        }
        with target.open("w", encoding="utf-8") as handle:
            parser.write(handle)

    def import_ini(self, source: Path) -> AppConfig:
        parser = configparser.ConfigParser()
        parser.read(source, encoding="utf-8")
        data = {}
        if parser.has_section("monitor"):
            section = parser["monitor"]
            data["monitor"] = {
                "sampling_interval_seconds": section.getfloat("sampling_interval_seconds", 2.0),
                "top_n_cpu": section.getint("top_n_cpu", 8),
                "top_n_memory": section.getint("top_n_memory", 8),
                "retention_days": section.getint("retention_days", 30),
                "start_minimized": section.getboolean("start_minimized", False),
                "close_to_tray": section.getboolean("close_to_tray", True),
                "enable_tray": section.getboolean("enable_tray", True),
                "auto_start": section.getboolean("auto_start", False),
                "theme": section.get("theme", "dark"),
                "database_path": section.get("database_path", "runtime/procwatch.sqlite3"),
            }
        return AppConfig.model_validate(data or DEFAULT_CONFIG.model_dump())
