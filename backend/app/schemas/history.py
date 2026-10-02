from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RunHistoryResponse(BaseModel):
    id: str
    report_id: str
    run_at: datetime
    period_type: str
    period_start: str
    period_end: str
    status: str
    duration_seconds: float
    metrics_data: dict[str, Any]
    telegram_delivered: bool
    telegram_error: str | None = None
    sheets_delivered: bool
    sheets_error: str | None = None
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
