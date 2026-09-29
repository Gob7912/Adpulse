from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

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
    telegram_error: Optional[str] = None
    sheets_delivered: bool
    sheets_error: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
