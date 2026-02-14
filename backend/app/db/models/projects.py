from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Enum, String, DateTime, Text, text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.domain.projects import ProjectStatus
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .users import Users
    from .targets import Targets
    from .runs import Runs


class Projects(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    project_status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, name="project_status_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False, server_default=text("'active'"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # foreign keys
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA}.users.id", ondelete="CASCADE"), nullable=False)

    # relationships
    owner: Mapped[Users] = relationship("Users", back_populates="projects")
    targets: Mapped[list[Targets]] = relationship("Targets", back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list[Runs]] = relationship("Runs", back_populates="project", cascade="all, delete-orphan")
