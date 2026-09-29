from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class RunHistory(Base):
    __tablename__ = "run_histories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    period_type: Mapped[str] = mapped_column(String(20), default="daily")
    period_start: Mapped[str] = mapped_column(String(30))
    period_end: Mapped[str] = mapped_column(String(30))
    
    # 'success', 'failed', 'partial'
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    # Executed report data snapshot
    metrics_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Channel statuses
    telegram_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_error: Mapped[str] = mapped_column(Text, nullable=True)
    sheets_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    sheets_error: Mapped[str] = mapped_column(Text, nullable=True)

    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    report: Mapped["Report"] = relationship("Report", back_populates="run_histories")
    user: Mapped["User"] = relationship("User", back_populates="run_histories")
