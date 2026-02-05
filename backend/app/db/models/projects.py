from __future__ import annotations
from sqlalchemy import Enum, String, DateTime, Text, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.domain.projects import ProjectStatus
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid


class Projects(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    project_status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, name="project_status_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False, server_default=text("'active'"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # foreign key and relationship



if __name__ == "__main__":
    pass
