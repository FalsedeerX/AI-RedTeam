from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum, String, Text, DateTime, text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.target import TargetType
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .projects import Projects
    from .runs import Runs


class Targets(Base):
    __tablename__ = "targets"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType, name="target_type_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # foreign keys
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.projects.id", ondelete="CASCADE"), nullable=False)

    # relationships
    project: Mapped[Projects] = relationship("Projects", back_populates="targets")
    runs: Mapped[list[Runs]] = relationship("Runs", back_populates="target")
