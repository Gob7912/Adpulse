from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.schemas.destination import DestinationResponse

class ReportCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    meta_account_id: str
    meta_account_name: str
    currency: str = "USD"
    account_timezone: str = "UTC"
    campaign_scope_type: str = "all"  # 'all', 'filtered', 'specific'
    campaign_filter_goals: list[str] = []
    campaign_filter_name: Optional[str] = None
    specific_campaign_ids: list[str] = []
    metrics: list[str] = []
    smart_metric_detection: bool = True
    metric_labels: dict[str, str] = {}
    metric_lang: str = "ru"
    periodicity: str = "daily"  # 'daily', 'weekly', 'monthly'
    schedule_time: str = "08:00"
    schedule_weekday: Optional[int] = None
    schedule_monthday: Optional[int] = None
    send_timezone: str = "Asia/Tashkent"
    
    # Destination setup from Step 1 & Step 5
    delivery_channels: list[str] = ["telegram"]  # 'telegram', 'google_sheets'
    sheets_url: Optional[str] = None
    sheets_tab_name: Optional[str] = "Sheet1"

class ReportUpdateRequest(BaseModel):
    name: Optional[str] = None
    meta_account_id: Optional[str] = None
    meta_account_name: Optional[str] = None
    currency: Optional[str] = None
    account_timezone: Optional[str] = None
    campaign_scope_type: Optional[str] = None
    campaign_filter_goals: Optional[list[str]] = None
    campaign_filter_name: Optional[str] = None
    specific_campaign_ids: Optional[list[str]] = None
    metrics: Optional[list[str]] = None
    smart_metric_detection: Optional[bool] = None
    metric_labels: Optional[dict[str, str]] = None
    metric_lang: Optional[str] = None
    periodicity: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_weekday: Optional[int] = None
    schedule_monthday: Optional[int] = None
    send_timezone: Optional[str] = None
    is_active: Optional[bool] = None
    delivery_channels: Optional[list[str]] = None
    sheets_url: Optional[str] = None
    sheets_tab_name: Optional[str] = None

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
    campaign_filter_name: Optional[str]
    specific_campaign_ids: list[str]
    metrics: list[str]
    smart_metric_detection: bool
    metric_labels: dict[str, str]
    metric_lang: str
    periodicity: str
    schedule_time: str
    schedule_weekday: Optional[int]
    schedule_monthday: Optional[int]
    send_timezone: str
    is_active: bool
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
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
