from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Boolean, DateTime, Integer, BigInteger, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Destination(Base):
    __tablename__ = "destinations"

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
    # 'telegram' or 'google_sheets'
    destination_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Telegram specific attributes
    # 'personal' or 'group_channel'
    telegram_target_type: Mapped[str] = mapped_column(String(20), nullable=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    telegram_thread_id: Mapped[int] = mapped_column(Integer, nullable=True)  # For Telegram Forum topics
    telegram_chat_title: Mapped[str] = mapped_column(String(255), nullable=True)
    one_time_code: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Google Sheets specific attributes
    sheets_url: Mapped[str] = mapped_column(Text, nullable=True)
    sheets_spreadsheet_id: Mapped[str] = mapped_column(String(100), nullable=True)
    sheets_tab_name: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    report: Mapped["Report"] = relationship("Report", back_populates="destinations")
