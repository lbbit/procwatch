from __future__ import annotations

from datetime import UTC, datetime

import psutil

from procwatch.models import ProcessMetric, SystemSnapshot


def _safe_name(proc: psutil.Process) -> str:
    try:
        return proc.name() or f"pid-{proc.pid}"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return f"pid-{proc.pid}"


class ProcessSampler:
    def sample(
        self,
        top_n_cpu: int,
        top_n_memory: int,
    ) -> tuple[list[ProcessMetric], list[ProcessMetric]]:
        processes: list[ProcessMetric] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                mem = proc.info.get("memory_info")
                rss = float(getattr(mem, "rss", 0.0)) / (1024 * 1024)
                processes.append(
                    ProcessMetric(
                        pid=int(proc.info.get("pid") or 0),
                        process_name=proc.info.get("name") or _safe_name(proc),
                        cpu_percent=float(proc.info.get("cpu_percent") or 0.0),
                        memory_mb=round(rss, 2),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top_cpu = sorted(processes, key=lambda item: item.cpu_percent, reverse=True)[:top_n_cpu]
        top_memory = sorted(processes, key=lambda item: item.memory_mb, reverse=True)[:top_n_memory]
        return top_cpu, top_memory


class SystemSampler:
    def __init__(self) -> None:
        psutil.cpu_percent(interval=None)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.process_sampler = ProcessSampler()

    def sample(self, top_n_cpu: int, top_n_memory: int) -> SystemSnapshot:
        virtual_memory = psutil.virtual_memory()
        top_cpu, top_memory = self.process_sampler.sample(top_n_cpu, top_n_memory)
        return SystemSnapshot(
            timestamp=datetime.now(UTC),
            cpu_percent=psutil.cpu_percent(interval=None),
            memory_percent=float(virtual_memory.percent),
            total_memory_mb=round(virtual_memory.total / 1024 / 1024),
            used_memory_mb=round(
                (virtual_memory.total - virtual_memory.available) / 1024 / 1024
            ),
            top_cpu_processes=top_cpu,
            top_memory_processes=top_memory,
        )
