from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from procwatch.models import ProcessMetric, SystemSnapshot


class Base(DeclarativeBase):
    pass


class SystemSample(Base):
    __tablename__ = "system_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    cpu_percent: Mapped[float] = mapped_column(Float)
    memory_percent: Mapped[float] = mapped_column(Float)
    total_memory_mb: Mapped[int] = mapped_column(Integer)
    used_memory_mb: Mapped[int] = mapped_column(Integer)
    process_samples: Mapped[list[ProcessSample]] = relationship(back_populates="system_sample")


class ProcessSample(Base):
    __tablename__ = "process_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_sample_id: Mapped[int] = mapped_column(ForeignKey("system_samples.id"), index=True)
    category: Mapped[str] = mapped_column(String(16), index=True)
    pid: Mapped[int] = mapped_column(Integer, index=True)
    process_name: Mapped[str] = mapped_column(String(260))
    cpu_percent: Mapped[float] = mapped_column(Float)
    memory_mb: Mapped[float] = mapped_column(Float)
    system_sample: Mapped[SystemSample] = relationship(back_populates="process_samples")


@dataclass(slots=True)
class HistoryPoint:
    sample_id: int
    timestamp: datetime
    cpu_percent: float
    memory_percent: float


class Database:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def insert_snapshot(self, snapshot: SystemSnapshot) -> None:
        with Session(self.engine) as session:
            system_sample = SystemSample(
                ts=snapshot.timestamp,
                cpu_percent=snapshot.cpu_percent,
                memory_percent=snapshot.memory_percent,
                total_memory_mb=snapshot.total_memory_mb,
                used_memory_mb=snapshot.used_memory_mb,
            )
            session.add(system_sample)
            session.flush()
            for category, metrics in (
                ("cpu", snapshot.top_cpu_processes),
                ("memory", snapshot.top_memory_processes),
            ):
                for item in metrics:
                    session.add(
                        ProcessSample(
                            system_sample_id=system_sample.id,
                            category=category,
                            pid=item.pid,
                            process_name=item.process_name,
                            cpu_percent=item.cpu_percent,
                            memory_mb=item.memory_mb,
                        )
                    )
            session.commit()

    def recent_system_samples(self, limit: int = 300) -> list[SystemSample]:
        with Session(self.engine) as session:
            stmt = select(SystemSample).order_by(SystemSample.ts.desc()).limit(limit)
            return list(session.scalars(stmt).all())

    def history_points(self, limit: int = 2000) -> list[HistoryPoint]:
        with Session(self.engine) as session:
            stmt = select(SystemSample).order_by(SystemSample.ts.desc()).limit(limit)
            rows = list(session.scalars(stmt).all())
        rows.reverse()
        return [
            HistoryPoint(
                sample_id=row.id,
                timestamp=row.ts,
                cpu_percent=row.cpu_percent,
                memory_percent=row.memory_percent,
            )
            for row in rows
        ]

    def processes_for_sample(self, sample_id: int, category: str) -> list[ProcessMetric]:
        with Session(self.engine) as session:
            stmt = (
                select(ProcessSample)
                .where(
                    ProcessSample.system_sample_id == sample_id,
                    ProcessSample.category == category,
                )
                .order_by(ProcessSample.cpu_percent.desc(), ProcessSample.memory_mb.desc())
            )
            rows = list(session.scalars(stmt).all())
        return [
            ProcessMetric(
                pid=row.pid,
                process_name=row.process_name,
                cpu_percent=row.cpu_percent,
                memory_mb=row.memory_mb,
            )
            for row in rows
        ]

    def purge_older_than(self, cutoff: datetime) -> None:
        with Session(self.engine) as session:
            old_ids = list(
                session.scalars(select(SystemSample.id).where(SystemSample.ts < cutoff)).all()
            )
            if not old_ids:
                return
            session.query(ProcessSample).filter(ProcessSample.system_sample_id.in_(old_ids)).delete(
                synchronize_session=False
            )
            session.query(SystemSample).filter(SystemSample.id.in_(old_ids)).delete(
                synchronize_session=False
            )
            session.commit()
