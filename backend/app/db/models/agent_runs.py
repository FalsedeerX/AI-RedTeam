from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import settings
from app.db.base import Base
from datetime import datetime
import uuid


class AgentRuns(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA}.projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA}.reports.id", ondelete="SET NULL"),
        nullable=True,
    )
