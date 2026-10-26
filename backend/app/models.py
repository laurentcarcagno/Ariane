from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportRecord(Base):
    """One analysed harness. `customer_id` scopes every read and write (see ImportRepository)."""

    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    plugin: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    drawing_name: Mapped[str] = mapped_column(String(255))
    bom_name: Mapped[str] = mapped_column(String(255))
    part_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    errors: Mapped[int] = mapped_column(default=0)
    warnings: Mapped[int] = mapped_column(default=0)
    model: Mapped[dict] = mapped_column(JSON)
