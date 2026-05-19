from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.models.base import Base


class EvalKind(str, enum.Enum):
    CLASSIFICATION = "classification"
    RAG = "rag"


class EvalReport(Base):
    __tablename__ = "eval_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[EvalKind] = mapped_column(
        Enum(EvalKind, name="eval_kind", values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(Text(), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    minio_key: Mapped[str] = mapped_column(Text(), nullable=False)
    previous_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    passed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
