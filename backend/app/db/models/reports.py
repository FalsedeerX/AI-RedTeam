from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, String, Text, DateTime, text, func, ForeignKey
from app.domain.reports import ReportFormat
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .runs import Runs


class Reports(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    report_format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat, name="report_format_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False)

    # foreign keys
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.runs.id", ondelete="CASCADE"), nullable=False)

    # relationships
    run: Mapped[Runs] = relationship("Runs", back_populates="reports")
