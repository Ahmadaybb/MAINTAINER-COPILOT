from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.models.base import Base


class WidgetConfig(Base):
    __tablename__ = "widget_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    theme: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    allowed_origins: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False, default=list)
    greeting: Mapped[str] = mapped_column(Text(), nullable=False)
    enabled_tools: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False, default=list)
    host_token_verify_key: Mapped[str] = mapped_column(Text(), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

