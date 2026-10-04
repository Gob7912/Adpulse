from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.destination import DestinationResponse


class ReportCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    meta_account_id: str
    meta_account_name: str
    currency: str = "USD"
    account_timezone: str = "UTC"
    campaign_scope_type: str = "all"  # 'all', 'filtered', 'specific'
    campaign_filter_goals: list[str] = []
    campaign_filter_name: str | None = None
    specific_campaign_ids: list[str] = []
    metrics: list[str] = []
    smart_metric_detection: bool = True
    metric_labels: dict[str, str] = {}
    metric_lang: str = "ru"
    periodicity: str = "daily"  # 'daily', 'weekly', 'monthly'
    schedule_time: str = "08:00"
    schedule_weekday: int | None = None
    schedule_monthday: int | None = None
    send_timezone: str = "Asia/Tashkent"
    show_comparison: bool = True
    
    # Destination setup from Step 1 & Step 5
    delivery_channels: list[str] = ["telegram"]  # 'telegram', 'google_sheets'
    sheets_url: str | None = None
    sheets_tab_name: str | None = "Sheet1"

class ReportUpdateRequest(BaseModel):
    name: str | None = None
    meta_account_id: str | None = None
    meta_account_name: str | None = None
    currency: str | None = None
    account_timezone: str | None = None
    campaign_scope_type: str | None = None
    campaign_filter_goals: list[str] | None = None
    campaign_filter_name: str | None = None
    specific_campaign_ids: list[str] | None = None
    metrics: list[str] | None = None
    smart_metric_detection: bool | None = None
    metric_labels: dict[str, str] | None = None
    metric_lang: str | None = None
    periodicity: str | None = None
    schedule_time: str | None = None
    schedule_weekday: int | None = None
    schedule_monthday: int | None = None
    send_timezone: str | None = None
    show_comparison: bool | None = None
    is_active: bool | None = None
    delivery_channels: list[str] | None = None
    sheets_url: str | None = None
    sheets_tab_name: str | None = None
    reset_telegram_code: bool | None = None

class ReportResponse(BaseModel):
    id: str
    user_id: int
    name: str
    meta_account_id: str
    meta_account_name: str
    currency: str
    account_timezone: str
    campaign_scope_type: str
    campaign_filter_goals: list[str]
    campaign_filter_name: str | None
    specific_campaign_ids: list[str]
    metrics: list[str]
    smart_metric_detection: bool
    metric_labels: dict[str, str]
    metric_lang: str
    periodicity: str
    schedule_time: str
    schedule_weekday: int | None
    schedule_monthday: int | None
    send_timezone: str
    show_comparison: bool = True
    is_active: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    last_run_error: str | None = None
    created_at: datetime
    updated_at: datetime
    destinations: list[DestinationResponse] = []

    class Config:
        from_attributes = True

class ReportLivePreviewRequest(BaseModel):
    metrics: list[str]
    metric_labels: dict[str, str] = {}
    lang: str = "ru"
    currency: str = "USD"
    periodicity: str = "daily"
    report_name: str = "Daily Report"

class ReportLivePreviewResponse(BaseModel):
    formatted_text: str
    sample_values: dict[str, Any]
