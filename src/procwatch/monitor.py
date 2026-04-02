from __future__ import annotations

from datetime import UTC, datetime

import psutil

from procwatch.models import ProcessMetric, SystemSnapshot

SKIP_PROCESS_NAMES = {
    "system idle process",
    "idle",
    "_total",
}


class ProcessSampler:
    def __init__(self) -> None:
        self._prime_cpu_counters()

    def _prime_cpu_counters(self) -> None:
        psutil.cpu_percent(interval=None)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _is_noise_process(self, process_name: str) -> bool:
        return process_name.strip().lower() in SKIP_PROCESS_NAMES

    def sample(
        self,
        top_n_cpu: int,
        top_n_memory: int,
    ) -> tuple[list[ProcessMetric], list[ProcessMetric]]:
        processes: list[ProcessMetric] = []
        cpu_count = max(1, psutil.cpu_count() or 1)
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                process_name = str(proc.info.get("name") or f"pid-{proc.pid}")
                if self._is_noise_process(process_name):
                    continue
                mem = proc.info.get("memory_info")
                rss = float(getattr(mem, "rss", 0.0)) / (1024 * 1024)
                raw_cpu = float(proc.info.get("cpu_percent") or 0.0)
                normalized_cpu = max(0.0, min(raw_cpu / cpu_count, 100.0))
                processes.append(
                    ProcessMetric(
                        pid=int(proc.info.get("pid") or 0),
                        process_name=process_name,
                        cpu_percent=round(normalized_cpu, 1),
                        memory_mb=round(rss, 1),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top_cpu = sorted(processes, key=lambda item: item.cpu_percent, reverse=True)[:top_n_cpu]
        top_memory = sorted(processes, key=lambda item: item.memory_mb, reverse=True)[:top_n_memory]
        return top_cpu, top_memory


class SystemSampler:
    def __init__(self) -> None:
        self.process_sampler = ProcessSampler()

    def sample(self, top_n_cpu: int, top_n_memory: int) -> SystemSnapshot:
        virtual_memory = psutil.virtual_memory()
        total_cpu_percent = psutil.cpu_percent(interval=0.15)
        top_cpu, top_memory = self.process_sampler.sample(top_n_cpu, top_n_memory)
        return SystemSnapshot(
            timestamp=datetime.now(UTC),
            cpu_percent=round(total_cpu_percent, 1),
            memory_percent=float(virtual_memory.percent),
            total_memory_mb=round(virtual_memory.total / 1024 / 1024),
            used_memory_mb=round(
                (virtual_memory.total - virtual_memory.available) / 1024 / 1024
            ),
            top_cpu_processes=top_cpu,
            top_memory_processes=top_memory,
        )
