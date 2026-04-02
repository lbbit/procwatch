from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ProcessMetric:
    pid: int
    process_name: str
    cpu_percent: float
    memory_mb: float


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    total_memory_mb: int
    used_memory_mb: int
    top_cpu_processes: list[ProcessMetric]
    top_memory_processes: list[ProcessMetric]
