import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.destination import Destination
from app.models.run_history import RunHistory
from app.schemas.report import (
    ReportCreateRequest,
    ReportUpdateRequest,
    ReportResponse,
    ReportLivePreviewRequest,
    ReportLivePreviewResponse
)
from app.schemas.destination import DestinationResponse
from app.services.scheduler_service import SchedulerService
from app.services.report_engine import ReportEngine
from app.services.sheets_service import SheetsService
from app.services.meta_metrics import METRIC_DEFINITIONS
from app.services.telegram_links import (
    build_telegram_deep_link,
    clean_and_validate_bot_username,
    clean_and_validate_start_code,
)
from app.services.telegram_sender import telegram_sender
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

def _build_destination_response(dest: Destination, bot_username: Optional[str] = None) -> DestinationResponse:
    deep_link_personal = None
    deep_link_group = None
    link_err = None
    cleaned_bot = None

    if dest.destination_type == "telegram":
        cleaned_bot, bot_err = clean_and_validate_bot_username(bot_username or settings.TELEGRAM_BOT_USERNAME)
        cleaned_code, code_err = clean_and_validate_start_code(dest.one_time_code)
        link_err = bot_err or code_err

        if cleaned_bot and cleaned_code:
            deep_link_personal = build_telegram_deep_link(cleaned_bot, cleaned_code, is_group=False)
            deep_link_group = build_telegram_deep_link(cleaned_bot, cleaned_code, is_group=True)

    return DestinationResponse(
        id=dest.id,
        report_id=dest.report_id,
        destination_type=dest.destination_type,
        is_enabled=dest.is_enabled,
        telegram_target_type=dest.telegram_target_type,
        telegram_chat_id=dest.telegram_chat_id,
        telegram_thread_id=dest.telegram_thread_id,
        telegram_chat_title=dest.telegram_chat_title,
        one_time_code=dest.one_time_code,
        is_connected=dest.is_connected,
        sheets_url=dest.sheets_url,
        sheets_spreadsheet_id=dest.sheets_spreadsheet_id,
        sheets_tab_name=dest.sheets_tab_name,
        deep_link_personal=deep_link_personal,
        deep_link_group=deep_link_group,
        bot_username=cleaned_bot,
        link_error=link_err
    )

def _build_report_response(report: Report, bot_username: Optional[str] = None) -> ReportResponse:
    dest_responses = [_build_destination_response(d, bot_username=bot_username) for d in report.destinations]
    return ReportResponse(
        id=report.id,
        user_id=report.user_id,
        name=report.name,
        meta_account_id=report.meta_account_id,
        meta_account_name=report.meta_account_name,
        currency=report.currency,
        account_timezone=report.account_timezone,
        campaign_scope_type=report.campaign_scope_type,
        campaign_filter_goals=report.campaign_filter_goals or [],
        campaign_filter_name=report.campaign_filter_name,
        specific_campaign_ids=report.specific_campaign_ids or [],
        metrics=report.metrics or [],
        smart_metric_detection=report.smart_metric_detection,
        metric_labels=report.metric_labels or {},
        metric_lang=report.metric_lang or "ru",
        periodicity=report.periodicity,
        schedule_time=report.schedule_time,
        schedule_weekday=report.schedule_weekday,
        schedule_monthday=report.schedule_monthday,
        send_timezone=report.send_timezone,
        is_active=report.is_active,
        next_run_at=report.next_run_at,
        last_run_at=report.last_run_at,
        last_run_status=report.last_run_status,
        last_run_error=report.last_run_error,
        created_at=report.created_at,
        updated_at=report.updated_at,
        destinations=dest_responses
    )

@router.get("", response_model=list[ReportResponse])
async def list_reports(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
    )
    result = await db.execute(query)
    reports = result.scalars().all()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return [_build_report_response(r, bot_username=bot_username) for r in reports]

@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Calculate next run timestamp
    next_run = SchedulerService.calculate_next_run(
        periodicity=data.periodicity,
        schedule_time_str=data.schedule_time,
        send_timezone_str=data.send_timezone,
        schedule_weekday=data.schedule_weekday,
        schedule_monthday=data.schedule_monthday,
        account_tz_str=data.account_timezone
    )

    report = Report(
        user_id=user.id,
        name=data.name,
        meta_account_id=data.meta_account_id,
        meta_account_name=data.meta_account_name,
        currency=data.currency,
        account_timezone=data.account_timezone,
        campaign_scope_type=data.campaign_scope_type,
        campaign_filter_goals=data.campaign_filter_goals,
        campaign_filter_name=data.campaign_filter_name,
        specific_campaign_ids=data.specific_campaign_ids,
        metrics=data.metrics,
        smart_metric_detection=data.smart_metric_detection,
        metric_labels=data.metric_labels,
        metric_lang=data.metric_lang,
        periodicity=data.periodicity,
        schedule_time=data.schedule_time,
        schedule_weekday=data.schedule_weekday,
        schedule_monthday=data.schedule_monthday,
        send_timezone=data.send_timezone,
        is_active=True,
        next_run_at=next_run
    )
    db.add(report)
    await db.flush()

    # Create destinations
    channels = data.delivery_channels or ["telegram"]
    if "telegram" in channels:
        one_time_code = secrets.token_hex(16)
        tg_dest = Destination(
            report_id=report.id,
            destination_type="telegram",
            is_enabled=True,
            telegram_target_type="personal",
            one_time_code=one_time_code,
            is_connected=False
        )
        db.add(tg_dest)

    if "google_sheets" in channels:
        sheet_id = SheetsService.extract_spreadsheet_id(data.sheets_url or "") if data.sheets_url else None
        sheets_dest = Destination(
            report_id=report.id,
            destination_type="google_sheets",
            is_enabled=True,
            sheets_url=data.sheets_url,
            sheets_spreadsheet_id=sheet_id,
            sheets_tab_name=data.sheets_tab_name or "Sheet1",
            is_connected=bool(sheet_id)
        )
        db.add(sheets_dest)

    await db.commit()

    # Reload with destinations
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report.id)
    )
    result = await db.execute(query)
    saved_report = result.scalars().first()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()

    return _build_report_response(saved_report, bot_username=bot_username)

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return _build_report_response(report, bot_username=bot_username)

@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    data: ReportUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    update_dict = data.model_dump(exclude_unset=True)

    # Handle delivery channels and destination configuration
    delivery_channels = update_dict.pop("delivery_channels", None)
    sheets_url = update_dict.pop("sheets_url", None)
    sheets_tab_name = update_dict.pop("sheets_tab_name", None)

    for k, v in update_dict.items():
        setattr(report, k, v)

    # If destinations need update
    if delivery_channels is not None:
        existing_types = {d.destination_type: d for d in report.destinations}
        if "telegram" in delivery_channels and "telegram" not in existing_types:
            one_time_code = secrets.token_hex(16)
            db.add(Destination(
                report_id=report.id,
                destination_type="telegram",
                is_enabled=True,
                telegram_target_type="personal",
                one_time_code=one_time_code,
                is_connected=False
            ))
        elif "telegram" not in delivery_channels and "telegram" in existing_types:
            for d in report.destinations:
                if d.destination_type == "telegram":
                    d.is_enabled = False

        if "google_sheets" in delivery_channels:
            sheet_id = SheetsService.extract_spreadsheet_id(sheets_url or "") if sheets_url else None
            sheets_dest = existing_types.get("google_sheets")
            if not sheets_dest:
                db.add(Destination(
                    report_id=report.id,
                    destination_type="google_sheets",
                    is_enabled=True,
                    sheets_url=sheets_url,
                    sheets_spreadsheet_id=sheet_id,
                    sheets_tab_name=sheets_tab_name or "Sheet1",
                    is_connected=bool(sheet_id)
                ))
            else:
                sheets_dest.is_enabled = True
                if sheets_url is not None:
                    sheets_dest.sheets_url = sheets_url
                    sheets_dest.sheets_spreadsheet_id = sheet_id
                    sheets_dest.is_connected = bool(sheet_id)
                if sheets_tab_name is not None:
                    sheets_dest.sheets_tab_name = sheets_tab_name
        elif "google_sheets" not in delivery_channels and "google_sheets" in existing_types:
            existing_types["google_sheets"].is_enabled = False
    else:
        # Update sheets url/tab if explicitly provided without changing channels
        for d in report.destinations:
            if d.destination_type == "google_sheets":
                if sheets_url is not None:
                    d.sheets_url = sheets_url
                    d.sheets_spreadsheet_id = SheetsService.extract_spreadsheet_id(sheets_url) if sheets_url else None
                    d.is_connected = bool(d.sheets_spreadsheet_id)
                if sheets_tab_name is not None:
                    d.sheets_tab_name = sheets_tab_name

    # If schedule changed, re-calculate next_run_at
    if any(k in update_dict for k in ("periodicity", "schedule_time", "send_timezone", "schedule_weekday", "schedule_monthday")):
        report.next_run_at = SchedulerService.calculate_next_run(
            periodicity=report.periodicity,
            schedule_time_str=report.schedule_time,
            send_timezone_str=report.send_timezone,
            schedule_weekday=report.schedule_weekday,
            schedule_monthday=report.schedule_monthday,
            account_tz_str=report.account_timezone
        )

    await db.commit()
    # Refresh with destinations
    res_refreshed = await db.execute(
        select(Report).options(selectinload(Report.destinations)).where(Report.id == report.id)
    )
    refreshed_report = res_refreshed.scalars().first()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return _build_report_response(refreshed_report, bot_username=bot_username)

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Report).where(Report.id == report_id, Report.user_id == user.id)
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    await db.delete(report)
    await db.commit()
    return {"message": "Отчёт успешно удален"}

@router.post("/{report_id}/pause", response_model=ReportResponse)
async def pause_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    report.is_active = False
    await db.commit()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return _build_report_response(report, bot_username=bot_username)

@router.post("/{report_id}/resume", response_model=ReportResponse)
async def resume_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    result = await db.execute(query)
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    report.is_active = True
    report.next_run_at = SchedulerService.calculate_next_run(
        periodicity=report.periodicity,
        schedule_time_str=report.schedule_time,
        send_timezone_str=report.send_timezone,
        schedule_weekday=report.schedule_weekday,
        schedule_monthday=report.schedule_monthday,
        account_tz_str=report.account_timezone
    )
    await db.commit()
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return _build_report_response(report, bot_username=bot_username)

@router.post("/{report_id}/duplicate", response_model=ReportResponse)
async def duplicate_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == report_id, Report.user_id == user.id)
    )
    result = await db.execute(query)
    original = result.scalars().first()
    if not original:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    new_report = Report(
        user_id=user.id,
        name=f"{original.name} (Копия)",
        meta_account_id=original.meta_account_id,
        meta_account_name=original.meta_account_name,
        currency=original.currency,
        account_timezone=original.account_timezone,
        campaign_scope_type=original.campaign_scope_type,
        campaign_filter_goals=list(original.campaign_filter_goals or []),
        campaign_filter_name=original.campaign_filter_name,
        specific_campaign_ids=list(original.specific_campaign_ids or []),
        metrics=list(original.metrics or []),
        smart_metric_detection=original.smart_metric_detection,
        metric_labels=dict(original.metric_labels or {}),
        metric_lang=original.metric_lang,
        periodicity=original.periodicity,
        schedule_time=original.schedule_time,
        schedule_weekday=original.schedule_weekday,
        schedule_monthday=original.schedule_monthday,
        send_timezone=original.send_timezone,
        is_active=False
    )
    db.add(new_report)
    await db.flush()

    for d in original.destinations:
        new_d = Destination(
            report_id=new_report.id,
            destination_type=d.destination_type,
            is_enabled=d.is_enabled,
            telegram_target_type=d.telegram_target_type,
            one_time_code=secrets.token_hex(16) if d.destination_type == "telegram" else None,
            is_connected=False if d.destination_type == "telegram" else d.is_connected,
            sheets_url=d.sheets_url,
            sheets_spreadsheet_id=d.sheets_spreadsheet_id,
            sheets_tab_name=d.sheets_tab_name
        )
        db.add(new_d)

    await db.commit()

    query_new = (
        select(Report)
        .options(selectinload(Report.destinations))
        .where(Report.id == new_report.id)
    )
    res = await db.execute(query_new)
    bot_username, _ = await telegram_sender.get_runtime_bot_username()
    return _build_report_response(res.scalars().first(), bot_username=bot_username)

@router.post("/{report_id}/test-send")
async def trigger_test_send(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Executes a real test report run immediately and dispatches to connected destinations."""
    # Ensure user owns report
    query = select(Report).where(Report.id == report_id, Report.user_id == user.id)
    res = await db.execute(query)
    if not res.scalars().first():
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    result = await SchedulerService.execute_report(report_id=report_id, is_test=True)
    return result

@router.post("/live-preview", response_model=ReportLivePreviewResponse)
async def generate_live_preview(data: ReportLivePreviewRequest):
    """Returns real-time preview text formatted for Telegram with sample numbers."""
    sample_values = {}
    for key in data.metrics:
        defn = METRIC_DEFINITIONS.get(key)
        if defn:
            sample_values[key] = defn.sample_value
        else:
            sample_values[key] = 100.0

    preview_text = ReportEngine.build_telegram_message(
        report_name=data.report_name or "Daily Report",
        account_name="Sample Ad Account",
        currency=data.currency or "USD",
        periodicity=data.periodicity or "daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=data.metrics,
        metric_values=sample_values,
        custom_labels=data.metric_labels,
        lang=data.lang
    )

    return ReportLivePreviewResponse(
        formatted_text=preview_text,
        sample_values=sample_values
    )
