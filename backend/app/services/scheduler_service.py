import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.report import Report
from app.models.destination import Destination
from app.models.meta_connection import MetaConnection
from app.models.run_history import RunHistory
from app.security import decrypt_secret
from app.services.meta_client import MetaClient, MetaTokenExpiredError, MetaAPIError
from app.services.meta_metrics import OBJECTIVE_TO_METRICS
from app.services.report_engine import ReportEngine
from app.services.telegram_sender import telegram_sender
from app.services.sheets_service import sheets_service

logger = logging.getLogger("adpulse.scheduler")

class SchedulerService:
    @staticmethod
    def calculate_next_run(
        periodicity: str,
        schedule_time_str: str,  # "08:00"
        send_timezone_str: str,  # "Asia/Tashkent"
        schedule_weekday: int | None = None,  # 0=Monday .. 6=Sunday
        schedule_monthday: int | None = None, # 1..31
        from_dt: datetime | None = None,
        account_tz_str: str = "UTC"
    ) -> datetime:
        """
        Calculates the next run UTC datetime for a report schedule,
        guaranteeing the final data delay (default 6 hours) has passed.
        """
        try:
            user_tz = ZoneInfo(send_timezone_str)
        except Exception:
            user_tz = ZoneInfo("Asia/Tashkent")

        if from_dt:
            if from_dt.tzinfo is None:
                from_dt = from_dt.replace(tzinfo=timezone.utc)
            now_in_user_tz = from_dt.astimezone(user_tz)
        else:
            now_in_user_tz = datetime.now(user_tz)

        # Parse schedule_time
        try:
            hour_str, min_str = schedule_time_str.split(":")
            target_hour = int(hour_str)
            target_min = int(min_str)
        except Exception:
            target_hour = 8
            target_min = 0

        target_today = now_in_user_tz.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

        if periodicity == "daily":
            if now_in_user_tz < target_today:
                candidate = target_today
            else:
                candidate = target_today + timedelta(days=1)

        elif periodicity == "weekly":
            # Target weekday (0=Mon..6=Sun, default 0=Monday)
            target_w = schedule_weekday if schedule_weekday is not None else 0
            days_ahead = (target_w - now_in_user_tz.weekday()) % 7
            if days_ahead == 0 and now_in_user_tz >= target_today:
                days_ahead = 7
            candidate = (target_today + timedelta(days=days_ahead))

        elif periodicity == "monthly":
            # Target day of month (e.g. 1st)
            target_d = schedule_monthday if schedule_monthday is not None else 1
            # Try this month
            try:
                candidate_this_month = target_today.replace(day=target_d)
                if now_in_user_tz < candidate_this_month:
                    candidate = candidate_this_month
                else:
                    # Next month
                    month = candidate_this_month.month + 1
                    year = candidate_this_month.year
                    if month > 12:
                        month = 1
                        year += 1
                    candidate = candidate_this_month.replace(year=year, month=month)
            except ValueError:
                # Handle month with fewer days
                candidate = target_today + timedelta(days=30)
        else:
            candidate = target_today + timedelta(days=1)

        candidate_utc = candidate.astimezone(timezone.utc)

        # Enforce Final Data Delay verification
        # The data period ends at midnight of the previous day in the account timezone
        since_d, until_d, period_end_dt = ReportEngine.calculate_period_dates(
            periodicity, account_tz_str, reference_dt=candidate
        )
        is_ready, ready_at_utc = ReportEngine.check_final_data_delay(
            period_end_dt, account_tz_str, delay_hours=settings.FINAL_DATA_DELAY_HOURS
        )
        if candidate_utc < ready_at_utc:
            # Shift run to when data is officially finalized
            candidate_utc = ready_at_utc

        return candidate_utc

    @staticmethod
    async def execute_report(report_id: str, is_test: bool = False) -> dict:
        """Executes a report: fetches Meta data, computes metrics, delivers to destinations."""
        start_time = time.time()
        logger.info(f"Starting execution for report {report_id} (is_test={is_test})")

        async with AsyncSessionLocal() as session:
            # Load report with relations
            query = (
                select(Report)
                .options(
                    selectinload(Report.destinations),
                    selectinload(Report.user).selectinload(User.meta_connection)
                )
                .where(Report.id == report_id)
            )
            result = await session.execute(query)
            report = result.scalars().first()

            if not report:
                raise ValueError(f"Report {report_id} not found")

            # Determine period dates first so they are available for RunHistory
            since_date, until_date, period_end_dt = ReportEngine.calculate_period_dates(
                report.periodicity, report.account_timezone
            )

            def record_failure(error_msg: str, tg_err: str | None = None, sheets_err: str | None = None):
                duration = round(time.time() - start_time, 2)
                now_utc = datetime.now(timezone.utc)
                history = RunHistory(
                    report_id=report.id,
                    user_id=report.user_id,
                    run_at=now_utc,
                    period_type=report.periodicity,
                    period_start=since_date,
                    period_end=until_date,
                    status="failed",
                    duration_seconds=duration,
                    metrics_data={},
                    telegram_delivered=False,
                    telegram_error=tg_err,
                    sheets_delivered=False,
                    sheets_error=sheets_err,
                    error_message=error_msg
                )
                session.add(history)
                report.last_run_at = now_utc
                report.last_run_status = "failed"
                report.last_run_error = error_msg
                if not is_test:
                    report.next_run_at = SchedulerService.calculate_next_run(
                        periodicity=report.periodicity,
                        schedule_time_str=report.schedule_time,
                        send_timezone_str=report.send_timezone,
                        schedule_weekday=report.schedule_weekday,
                        schedule_monthday=report.schedule_monthday,
                        from_dt=now_utc,
                        account_tz_str=report.account_timezone
                    )

            # Check Meta connection
            meta_conn = report.user.meta_connection if report.user else None
            if not meta_conn or not meta_conn.encrypted_access_token:
                err_msg = "Meta-аккаунт не подключен или отсутствует токен доступа."
                record_failure(err_msg)
                await session.commit()
                return {"status": "failed", "error": err_msg}

            # Decrypt access token
            try:
                access_token = decrypt_secret(meta_conn.encrypted_access_token)
            except Exception as e:
                err_msg = f"Ошибка расшифровки токена: {e}"
                record_failure(err_msg)
                await session.commit()
                return {"status": "failed", "error": err_msg}

            meta_client = MetaClient(access_token=access_token)

            # Check final data delay unless it's a test run
            if not is_test:
                is_ready, ready_at_utc = ReportEngine.check_final_data_delay(
                    period_end_dt, report.account_timezone, delay_hours=settings.FINAL_DATA_DELAY_HOURS
                )
                if not is_ready:
                    logger.info(f"Report {report_id} data not final yet. Deferring to {ready_at_utc.isoformat()}")
                    report.next_run_at = ready_at_utc
                    await session.commit()
                    return {"status": "deferred", "ready_at": ready_at_utc.isoformat()}

            # Resolve campaign IDs based on campaign_scope_type
            resolved_campaign_ids: list[str] | None = None
            try:
                if report.campaign_scope_type == "filtered":
                    campaigns = await meta_client.get_campaigns(report.meta_account_id)
                    matched_ids = []
                    goals = report.campaign_filter_goals or []
                    name_contains = (report.campaign_filter_name or "").strip().lower()

                    for c in campaigns:
                        obj = c.get("objective", "")
                        c_name = c.get("name", "").lower()

                        goal_matched = True
                        if goals:
                            # Match optimization goals
                            goal_matched = any(g in obj.upper() for g in goals)

                        name_matched = True
                        if name_contains:
                            name_matched = name_contains in c_name

                        if goal_matched and name_matched:
                            matched_ids.append(c.get("id"))

                    resolved_campaign_ids = matched_ids
                    # If smart detection is active, dynamically ensure relevant metrics are tracked
                    if report.smart_metric_detection and goals:
                        for g in goals:
                            for auto_m in OBJECTIVE_TO_METRICS.get(g, []):
                                if auto_m not in report.metrics:
                                    report.metrics.append(auto_m)

                elif report.campaign_scope_type == "specific":
                    resolved_campaign_ids = report.specific_campaign_ids or []
                else:
                    # 'all' campaigns: None triggers account-level insights across all
                    resolved_campaign_ids = None

                # Query Meta Insights with 3 retries for transient failures
                insight_data = {}
                if report.campaign_scope_type in ("filtered", "specific") and resolved_campaign_ids == []:
                    insight_data = {}
                else:
                    max_retries = 3
                    for attempt in range(1, max_retries + 1):
                        try:
                            insight_data = await meta_client.get_insights(
                                ad_account_id=report.meta_account_id,
                                since_date=since_date,
                                until_date=until_date,
                                campaign_ids=resolved_campaign_ids
                            )
                            break
                        except MetaTokenExpiredError:
                            raise
                        except Exception as exc:
                            if attempt < max_retries:
                                backoff = 2 ** (attempt - 1)
                                logger.warning(f"Meta API attempt {attempt} failed for report {report.id}: {exc}. Retrying in {backoff}s...")
                                await asyncio.sleep(backoff)
                            else:
                                raise

                # Compute metrics
                metrics_data = ReportEngine.compute_aggregated_metrics(insight_data)

            except MetaTokenExpiredError as exc:
                logger.error(f"Meta token expired for report {report.id}: {exc}")
                meta_conn.is_valid = False
                record_failure(str(exc))

                # Send alert to Telegram destinations if linked
                for dest in report.destinations:
                    if dest.destination_type == "telegram" and dest.is_connected and dest.telegram_chat_id:
                        try:
                            await telegram_sender.send_token_expired_alert(
                                chat_id=dest.telegram_chat_id,
                                report_name=report.name,
                                message_thread_id=dest.telegram_thread_id
                            )
                        except Exception as alert_err:
                            logger.error(f"Failed to send token expiration alert to Telegram: {alert_err}")

                await session.commit()
                return {"status": "failed", "error": str(exc), "code": 190}

            except MetaAPIError as exc:
                logger.error(f"Meta API error for report {report.id}: {exc}")
                record_failure(str(exc))
                await session.commit()
                return {"status": "failed", "error": str(exc)}

            except Exception as exc:
                logger.error(f"Unexpected error querying Meta for report {report.id}: {exc}", exc_info=True)
                record_failure(str(exc))
                await session.commit()
                return {"status": "failed", "error": str(exc)}

            # Deliver to Destinations
            tg_delivered = False
            tg_error = None
            sheets_delivered = False
            sheets_error = None

            for dest in report.destinations:
                if not dest.is_enabled:
                    continue

                if dest.destination_type == "telegram":
                    if dest.is_connected and dest.telegram_chat_id:
                        try:
                            # Detect template type from campaign_filter_goals or metrics
                            detected_type = None
                            goals = [str(g).upper() for g in (report.campaign_filter_goals or [])]
                            if any("LEAD" in g for g in goals):
                                detected_type = "lead_generation"
                            elif any("MESSAGE" in g for g in goals):
                                detected_type = "direct_messages"
                            elif any("AWARENESS" in g or "REACH" in g for g in goals):
                                detected_type = "brand_awareness"

                            msg_text = ReportEngine.build_telegram_message(
                                report_name=report.name,
                                account_name=report.meta_account_name,
                                currency=report.currency,
                                periodicity=report.periodicity,
                                since_date=since_date,
                                until_date=until_date,
                                selected_metrics=report.metrics or [],
                                metric_values=metrics_data,
                                custom_labels=report.metric_labels or {},
                                lang=report.metric_lang or "ru",
                                template_type=detected_type
                            )
                            await telegram_sender.send_message(
                                chat_id=dest.telegram_chat_id,
                                text=msg_text,
                                message_thread_id=dest.telegram_thread_id
                            )
                            tg_delivered = True
                        except Exception as e:
                            logger.error(f"Telegram delivery failed for destination {dest.id}: {e}")
                            tg_error = str(e)
                    else:
                        tg_error = "Чат Telegram ещё не привязан"

                elif dest.destination_type == "google_sheets":
                    if dest.sheets_spreadsheet_id:
                        try:
                            headers, row = ReportEngine.build_sheets_row_data(
                                report_name=report.name,
                                since_date=since_date,
                                until_date=until_date,
                                selected_metrics=report.metrics or [],
                                metric_values=metrics_data,
                                custom_labels=report.metric_labels or {},
                                lang=report.metric_lang or "ru"
                            )
                            await asyncio.to_thread(
                                sheets_service.append_report_row,
                                spreadsheet_id=dest.sheets_spreadsheet_id,
                                tab_name=dest.sheets_tab_name,
                                header_labels=headers,
                                row_values=row
                            )
                            sheets_delivered = True
                        except Exception as e:
                            logger.error(f"Google Sheets delivery failed: {e}")
                            sheets_error = str(e)
                    else:
                        sheets_error = "ID таблицы не указан"

            # Determine overall run status
            run_status = "success"
            if tg_error or sheets_error:
                run_status = "partial" if (tg_delivered or sheets_delivered) else "failed"

            duration = round(time.time() - start_time, 2)
            now_utc = datetime.now(timezone.utc)

            # Record RunHistory
            history = RunHistory(
                report_id=report.id,
                user_id=report.user_id,
                run_at=now_utc,
                period_type=report.periodicity,
                period_start=since_date,
                period_end=until_date,
                status=run_status,
                duration_seconds=duration,
                metrics_data=metrics_data,
                telegram_delivered=tg_delivered,
                telegram_error=tg_error,
                sheets_delivered=sheets_delivered,
                sheets_error=sheets_error,
                error_message=f"{tg_error or ''} {sheets_error or ''}".strip() or None
            )
            session.add(history)

            # Update report status and next_run_at
            report.last_run_at = now_utc
            report.last_run_status = run_status
            report.last_run_error = history.error_message

            if not is_test:
                # Schedule the subsequent run
                next_run = SchedulerService.calculate_next_run(
                    periodicity=report.periodicity,
                    schedule_time_str=report.schedule_time,
                    send_timezone_str=report.send_timezone,
                    schedule_weekday=report.schedule_weekday,
                    schedule_monthday=report.schedule_monthday,
                    from_dt=now_utc,
                    account_tz_str=report.account_timezone
                )
                report.next_run_at = next_run

            await session.commit()
            return {
                "status": run_status,
                "duration_seconds": duration,
                "metrics": metrics_data,
                "telegram_delivered": tg_delivered,
                "sheets_delivered": sheets_delivered,
                "telegram_error": tg_error,
                "sheets_error": sheets_error
            }

    @staticmethod
    async def run_worker_loop():
        """Continuous polling worker loop that fires scheduled reports."""
        logger.info("Scheduler worker loop started.")
        while True:
            try:
                now_utc = datetime.now(timezone.utc)
                async with AsyncSessionLocal() as session:
                    # Select reports due to run
                    query = (
                        select(Report)
                        .where(
                            Report.is_active == True,
                            Report.next_run_at != None,
                            Report.next_run_at <= now_utc
                        )
                        .limit(20)
                    )
                    result = await session.execute(query)
                    due_reports = result.scalars().all()

                    for report in due_reports:
                        # Prevent duplicate run by temporarily updating next_run_at
                        report.next_run_at = now_utc + timedelta(minutes=10)
                        await session.commit()

                        # Execute report asynchronously
                        asyncio.create_task(SchedulerService.execute_report(report.id, is_test=False))

            except Exception as e:
                logger.error(f"Error in scheduler worker loop: {e}", exc_info=True)

            await asyncio.sleep(30)

scheduler_service = SchedulerService()
