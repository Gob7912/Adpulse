
from pydantic import BaseModel, ConfigDict


class DestinationCreateRequest(BaseModel):
    destination_type: str  # "telegram" | "google_sheets"
    telegram_target_type: str | None = "personal"
    sheets_url: str | None = None
    sheets_tab_name: str | None = "Sheet1"

class DestinationResponse(BaseModel):
    id: str
    report_id: str
    destination_type: str
    is_enabled: bool = True
    telegram_target_type: str | None = None
    telegram_chat_id: int | None = None
    telegram_thread_id: int | None = None
    telegram_chat_title: str | None = None
    one_time_code: str | None = None
    is_connected: bool = False
    sheets_url: str | None = None
    sheets_spreadsheet_id: str | None = None
    sheets_tab_name: str | None = None
    deep_link_personal: str | None = None
    deep_link_group: str | None = None
    bot_username: str | None = None
    link_error: str | None = None

    model_config = ConfigDict(from_attributes=True)

class TelegramBotInfoResponse(BaseModel):
    bot_username: str | None = None
    is_configured: bool = False
    error: str | None = None

class GoogleSheetsServiceInfoResponse(BaseModel):
    service_account_email: str | None = None
    is_configured: bool = False

class GoogleSheetsVerifyRequest(BaseModel):
    sheets_url: str
    sheets_tab_name: str | None = None

class GoogleSheetsVerifyResponse(BaseModel):
    success: bool
    title: str | None = None
    tab_name: str | None = None
    message: str
    service_account_email: str | None = None

