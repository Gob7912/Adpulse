from pydantic import BaseModel, ConfigDict
from typing import Optional

class DestinationCreateRequest(BaseModel):
    destination_type: str  # "telegram" | "google_sheets"
    telegram_target_type: Optional[str] = "personal"
    sheets_url: Optional[str] = None
    sheets_tab_name: Optional[str] = "Sheet1"

class DestinationResponse(BaseModel):
    id: str
    report_id: str
    destination_type: str
    is_enabled: bool = True
    telegram_target_type: Optional[str] = None
    telegram_chat_id: Optional[int] = None
    telegram_thread_id: Optional[int] = None
    telegram_chat_title: Optional[str] = None
    one_time_code: Optional[str] = None
    is_connected: bool = False
    sheets_url: Optional[str] = None
    sheets_spreadsheet_id: Optional[str] = None
    sheets_tab_name: Optional[str] = None
    deep_link_personal: Optional[str] = None
    deep_link_group: Optional[str] = None
    bot_username: Optional[str] = None
    link_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TelegramBotInfoResponse(BaseModel):
    bot_username: Optional[str] = None
    is_configured: bool = False
    error: Optional[str] = None

class GoogleSheetsServiceInfoResponse(BaseModel):
    service_account_email: Optional[str] = None
    is_configured: bool = False

class GoogleSheetsVerifyRequest(BaseModel):
    sheets_url: str
    sheets_tab_name: Optional[str] = None

class GoogleSheetsVerifyResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    tab_name: Optional[str] = None
    message: str
    service_account_email: Optional[str] = None

