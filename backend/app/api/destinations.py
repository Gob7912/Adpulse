from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.destination import Destination
from app.schemas.destination import (
    GoogleSheetsVerifyRequest,
    GoogleSheetsVerifyResponse,
    DestinationResponse,
    TelegramBotInfoResponse
)
from app.services.sheets_service import sheets_service, SheetsService
from app.services.telegram_sender import telegram_sender
from app.api.deps import get_current_user
from app.api.reports import _build_destination_response

router = APIRouter(prefix="/destinations", tags=["destinations"])

@router.get("/telegram/bot-info", response_model=TelegramBotInfoResponse)
async def get_telegram_bot_info(user: User = Depends(get_current_user)):
    """
    Returns the real bot username retrieved at runtime via Telegram getMe (cached).
    Allows frontend to validate links without relying on build-time environment variables.
    """
    bot_username, error = await telegram_sender.get_runtime_bot_username()
    return TelegramBotInfoResponse(
        bot_username=bot_username,
        is_configured=bool(bot_username),
        error=error if not bot_username else None
    )

@router.post("/sheets/verify", response_model=GoogleSheetsVerifyResponse)
async def verify_google_sheet(
    data: GoogleSheetsVerifyRequest,
    user: User = Depends(get_current_user)
):
    """Verifies that the Google Service Account has access to the specified sheet."""
    spreadsheet_id = SheetsService.extract_spreadsheet_id(data.sheets_url)
    if not spreadsheet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректная ссылка на Google Таблицу"
        )

    res = sheets_service.verify_sheet_access(
        spreadsheet_id=spreadsheet_id,
        tab_name=data.sheets_tab_name
    )
    return GoogleSheetsVerifyResponse(
        success=res.get("success", False),
        title=res.get("title"),
        tab_name=res.get("tab_name"),
        message=res.get("message", "")
    )

@router.get("/{report_id}/status", response_model=list[DestinationResponse])
async def get_destination_status(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refreshes and returns the current connection status of destinations for a report."""
    query = (
        select(Destination)
        .join(Report, Destination.report_id == Report.id)
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    res = await db.execute(query)
    destinations = res.scalars().all()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return [_build_destination_response(d, bot_username=bot_username) for d in destinations]
