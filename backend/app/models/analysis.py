"""Persisted analysis metadata and results."""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, JSON, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Analysis(Base):
    """An image-analysis attempt and its output when real inference exists."""

    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name="ck_analyses_status"),
        CheckConstraint("image_size_bytes > 0 AND image_size_bytes <= 10485760", name="ck_analyses_image_size"),
        CheckConstraint(
            "image_content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_analyses_image_content_type",
        ),
        Index("ix_analyses_created_at", "created_at"),
        Index("ix_analyses_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default=text("'pending'"))
    image_content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    image_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
