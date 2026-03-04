from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, DateTime, text, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.config import settings
from app.db.base import Base
import uuid

if TYPE_CHECKING:
    from .projects import Projects


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # relationships
    projects: Mapped[list[Projects]] = relationship("Projects", back_populates="owner", cascade="all, delete-orphan")
