from __future__ import annotations
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, DateTime, text, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("app.gen_random_uuid()"))
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false")))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    projects: Mapped[list["Projects"]] = relationship("Projects", back_populates="owner", cascade="all, delete-orphan", passive_deletes=True)


if __name__ == "__main__":
    pass
