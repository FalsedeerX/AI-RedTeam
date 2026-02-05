from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum, Text, DateTime, text, func
from app.domain.findings import FindingSeverity, FindingType
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    pass


class Findings(Base):
    __tablename__ = "findings"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finding_type: Mapped[FindingType] = mapped_column(Enum(FindingType, name="finding_type_enum", schema=settings.DB_SCHEMA, native_enum=True), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(Enum)
