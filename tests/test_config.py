from pathlib import Path

from procwatch.config import AppConfig, SettingsService


def test_json_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "config.json")
    config = AppConfig()
    service.save(config)
    loaded = service.load()
    assert loaded.monitor.top_n_cpu == config.monitor.top_n_cpu


def test_ini_roundtrip(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "config.json")
    config = AppConfig()
    target = tmp_path / "config.ini"
    service.export_ini(config, target)
    loaded = service.import_ini(target)
    assert loaded.monitor.top_n_memory == config.monitor.top_n_memory
