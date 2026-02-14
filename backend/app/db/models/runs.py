from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, String, Text, DateTime, text, func, ForeignKey
from app.domain.runs import RunType, RunPurpose, RunStatus, RunOutputFormat
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .projects import Projects
    from .targets import Targets
    from .findings import Findings
    from .reports import Reports


class Runs(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    run_type: Mapped[RunType] = mapped_column(Enum(RunType, name="run_type_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=True)
    purpose: Mapped[RunPurpose] = mapped_column(Enum(RunPurpose, name="run_purpose_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False, server_default=text("'QUEUED'"))
    tool_name: Mapped[str] = mapped_column(String(64), nullable=True)
    tool_version: Mapped[str] = mapped_column(String(64), nullable=True)
    raw_command: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    output_format: Mapped[RunOutputFormat] = mapped_column(Enum(RunOutputFormat, name="run_output_format_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=True)

    # foreign keys
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.projects.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.targets.id", ondelete="SET NULL"), nullable=True)

    # relationships
    project: Mapped[Projects] = relationship("Projects", back_populates="runs")
    target: Mapped[Targets | None] = relationship("Targets", back_populates="runs")
    findings: Mapped[list[Findings]] = relationship("Findings", back_populates="run", cascade="all, delete-orphan")
    reports: Mapped[list[Reports]] = relationship("Reports", back_populates="run", cascade="all, delete-orphan")
