from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Meta Ad Account
    meta_account_id: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "act_123456789"
    meta_account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    account_timezone: Mapped[str] = mapped_column(String(100), default="UTC")

    # Campaign Scope
    # 'all', 'filtered', or 'specific'
    campaign_scope_type: Mapped[str] = mapped_column(String(20), default="all")
    # List of optimization goal keys, e.g. ["MESSAGES", "LEAD_GENERATION"]
    campaign_filter_goals: Mapped[list] = mapped_column(JSON, default=list)
    # Optional text substring to match campaign name
    campaign_filter_name: Mapped[str] = mapped_column(String(255), nullable=True)
    # List of specific campaign IDs if scope is 'specific'
    specific_campaign_ids: Mapped[list] = mapped_column(JSON, default=list)

    # Metrics configuration
    metrics: Mapped[list] = mapped_column(JSON, default=list)
    smart_metric_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    metric_labels: Mapped[dict] = mapped_column(JSON, default=dict)
    metric_lang: Mapped[str] = mapped_column(String(10), default="ru")

    # Schedule
    # 'daily', 'weekly', 'monthly'
    periodicity: Mapped[str] = mapped_column(String(20), default="daily")
    schedule_time: Mapped[str] = mapped_column(String(10), default="08:00")  # HH:MM
    schedule_weekday: Mapped[int] = mapped_column(Integer, nullable=True)  # 0-6 (0=Monday) for weekly
    schedule_monthday: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-31 for monthly
    send_timezone: Mapped[str] = mapped_column(String(100), default="Asia/Tashkent")

    # Runtime status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String(20), nullable=True)
    last_run_error: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reports", lazy="selectin")
    destinations: Mapped[list["Destination"]] = relationship(
        "Destination",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )
    run_histories: Mapped[list["RunHistory"]] = relationship(
        "RunHistory",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )
