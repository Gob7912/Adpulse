import asyncio
import calendar
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.destination import Destination
from app.models.meta_connection import MetaConnection
from app.models.report import Report
from app.models.run_history import RunHistory
from app.models.user import User
from app.security import decrypt_secret
from app.services.meta_client import MetaAPIError, MetaClient, MetaTokenExpiredError
from app.services.meta_metrics import OBJECTIVE_TO_METRICS
from app.services.report_engine import ReportEngine
from app.services.sheets_service import sheets_service
from app.services.telegram_sender import telegram_sender

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

        today_date = now_in_user_tz.date()
        target_today = datetime(
            today_date.year, today_date.month, today_date.day,
            target_hour, target_min, 0, 0, tzinfo=user_tz
        )

        if periodicity == "daily":
            if now_in_user_tz < target_today:
                candidate_date = today_date
            else:
                candidate_date = today_date + timedelta(days=1)
            candidate = datetime(
                candidate_date.year, candidate_date.month, candidate_date.day,
                target_hour, target_min, 0, 0, tzinfo=user_tz
            )

        elif periodicity == "weekly":
            # Target weekday (0=Mon..6=Sun, default 0=Monday)
            target_w = schedule_weekday if schedule_weekday is not None else 0
            days_ahead = (target_w - today_date.weekday()) % 7
            if days_ahead == 0 and now_in_user_tz >= target_today:
                days_ahead = 7
            candidate_date = today_date + timedelta(days=days_ahead)
            candidate = datetime(
                candidate_date.year, candidate_date.month, candidate_date.day,
                target_hour, target_min, 0, 0, tzinfo=user_tz
            )

        elif periodicity == "monthly":
            # Target day of month (e.g. 1st..31st)
            target_d = schedule_monthday if schedule_monthday is not None else 1
            days_in_this_month = calendar.monthrange(today_date.year, today_date.month)[1]
            actual_day_this_month = min(target_d, days_in_this_month)
            candidate_this_month = datetime(
                today_date.year, today_date.month, actual_day_this_month,
                target_hour, target_min, 0, 0, tzinfo=user_tz
            )

            if now_in_user_tz < candidate_this_month:
                candidate = candidate_this_month
            else:
                # Next calendar month
                next_year = today_date.year
                next_month = today_date.month + 1
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                days_in_next_month = calendar.monthrange(next_year, next_month)[1]
                actual_day_next_month = min(target_d, days_in_next_month)
                candidate = datetime(
                    next_year, next_month, actual_day_next_month,
                    target_hour, target_min, 0, 0, tzinfo=user_tz
                )
        else:
            candidate_date = today_date + timedelta(days=1)
            candidate = datetime(
                candidate_date.year, candidate_date.month, candidate_date.day,
                target_hour, target_min, 0, 0, tzinfo=user_tz
            )

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
    async def execute_report(
        report_id: str,
        is_test: bool = False,
        cache_bypass: bool = True
    ) -> dict:
        """Executes a report: fetches Meta data, computes metrics, delivers to destinations."""
        start_time = time.time()
        logger.info(f"Starting execution for report {report_id} (is_test={is_test}, cache_bypass={cache_bypass})")

        async with AsyncSessionLocal() as session:
            # Check local DB cache only when cache_bypass is explicitly False and not a test run
            if not cache_bypass and not is_test:
                cached_res = await session.execute(
                    select(RunHistory)
                    .where(RunHistory.report_id == report_id, RunHistory.status == "success")
                    .order_by(RunHistory.run_at.desc())
                    .limit(1)
                )
                cached_history = cached_res.scalars().first()
                if cached_history:
                    logger.info(f"Returning cached run history for report {report_id} (cache_bypass=False)")
                    return {
                        "status": cached_history.status,
                        "duration_seconds": cached_history.duration_seconds,
                        "metrics": cached_history.metrics_data,
                        "telegram_delivered": cached_history.telegram_delivered,
                        "sheets_delivered": cached_history.sheets_delivered,
                        "telegram_error": cached_history.telegram_error,
                        "sheets_error": cached_history.sheets_error,
                        "from_cache": True
                    }

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

            # Determine period dates: strictly use the ad account's timezone (both for regular and test runs)
            tz_to_use = report.account_timezone or "Asia/Tashkent"
            since_date, until_date, prev_since, prev_until, period_end_dt = ReportEngine.calculate_comparison_dates(
                periodicity=report.periodicity,
                account_tz_str=tz_to_use,
                is_test=is_test
            )
            should_compare = (
                not is_test
                and getattr(report, "show_comparison", True)
                and prev_since is not None
                and prev_until is not None
            )

            # Prevent duplicate runs and handle stalled sending (Two-Phase Execution)
            if not is_test:
                existing_run = await session.scalar(
                    select(RunHistory).where(
                        RunHistory.report_id == report.id,
                        RunHistory.period_start == since_date,
                        RunHistory.period_end == until_date,
                        RunHistory.is_test == False,
                        RunHistory.status.in_(["success", "no_data", "sending"])
                    )
                )
                if existing_run:
                    if existing_run.status in ("success", "no_data"):
                        logger.info(
                            f"Report {report.id} was already executed successfully for period {since_date}..{until_date}. "
                            "Skipping duplicate execution to prevent repeated Telegram notifications and Sheets rows."
                        )
                        now_utc = datetime.now(timezone.utc)
                        report.next_run_at = SchedulerService.calculate_next_run(
                            periodicity=report.periodicity,
                            schedule_time_str=report.schedule_time,
                            send_timezone_str=report.send_timezone,
                            schedule_weekday=report.schedule_weekday,
                            schedule_monthday=report.schedule_monthday,
                            from_dt=now_utc,
                            account_tz_str=report.account_timezone
                        )
                        await session.commit()
                        return {"status": "skipped", "message": "Already executed for this period"}
                    elif existing_run.status == "sending":
                        # Check timeout for stalled sending (15 minutes)
                        now_utc = datetime.now(timezone.utc)
                        run_at_tz = existing_run.run_at if existing_run.run_at.tzinfo else existing_run.run_at.replace(tzinfo=timezone.utc)
                        if (now_utc - run_at_tz) > timedelta(minutes=15):
                            logger.warning(
                                f"Run {existing_run.id} for report {report.id} was stuck in sending state for > 15m. "
                                "Marking as failed and advancing schedule (at-most-once semantics)."
                            )
                            existing_run.status = "failed"
                            existing_run.error_message = "Worker execution timed out in sending state"
                            report.last_run_status = "failed"
                            report.last_run_error = existing_run.error_message
                            report.next_run_at = SchedulerService.calculate_next_run(
                                periodicity=report.periodicity,
                                schedule_time_str=report.schedule_time,
                                send_timezone_str=report.send_timezone,
                                schedule_weekday=report.schedule_weekday,
                                schedule_monthday=report.schedule_monthday,
                                from_dt=now_utc,
                                account_tz_str=report.account_timezone
                            )
                            await session.commit()
                            return {"status": "skipped", "message": "Stalled sending run marked failed"}
                        else:
                            logger.info(f"Report {report.id} is currently being sent by another worker (status=sending). Skipping.")
                            return {"status": "skipped", "message": "Report is currently sending"}

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
                    is_test=is_test,
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
                prev_insight_data = None
                deltas = None

                if report.campaign_scope_type in ("filtered", "specific") and resolved_campaign_ids == []:
                    insight_data = {}
                elif should_compare:
                    max_retries = 3
                    for attempt in range(1, max_retries + 1):
                        try:
                            try:
                                multi_insights = await meta_client.get_multi_period_insights(
                                    ad_account_id=report.meta_account_id,
                                    periods=[(prev_since, prev_until), (since_date, until_date)],
                                    campaign_ids=resolved_campaign_ids,
                                    timezone_str=report.account_timezone
                                )
                                insight_data = multi_insights.get((since_date, until_date)) or {}
                                prev_insight_data = multi_insights.get((prev_since, prev_until))
                                break
                            except TypeError as te:
                                if "await" in str(te) or "coroutine" in str(te):
                                    insight_data = await meta_client.get_insights(
                                        ad_account_id=report.meta_account_id,
                                        since_date=since_date,
                                        until_date=until_date,
                                        campaign_ids=resolved_campaign_ids,
                                        timezone_str=report.account_timezone
                                    )
                                    should_compare = False
                                    break
                                raise
                        except MetaTokenExpiredError:
                            raise
                        except Exception as exc:
                            if attempt < max_retries:
                                backoff = 2 ** (attempt - 1)
                                logger.warning(f"Meta API attempt {attempt} failed for report {report.id}: {exc}. Retrying in {backoff}s...")
                                await asyncio.sleep(backoff)
                            else:
                                raise
                else:
                    max_retries = 3
                    for attempt in range(1, max_retries + 1):
                        try:
                            insight_data = await meta_client.get_insights(
                                ad_account_id=report.meta_account_id,
                                since_date=since_date,
                                until_date=until_date,
                                campaign_ids=resolved_campaign_ids,
                                timezone_str=report.account_timezone
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

                # Fetch campaign-level insights only if 'profile_visits' is selected in report
                need_campaign_insights = "profile_visits" in (report.metrics or [])
                camp_insights = None
                prev_camp_insights = None

                if need_campaign_insights and report.meta_account_id:
                    try:
                        camp_insights = await meta_client.get_campaign_insights(
                            ad_account_id=report.meta_account_id,
                            since_date=since_date,
                            until_date=until_date,
                            campaign_ids=resolved_campaign_ids,
                            use_account_attribution_setting=getattr(meta_client, "use_account_attribution_setting", True)
                        )
                    except Exception as c_err:
                        logger.warning(f"Could not fetch campaign insights for {report.id} ({since_date}..{until_date}): {c_err}")
                        camp_insights = None

                    if should_compare and prev_since and prev_until:
                        try:
                            prev_camp_insights = await meta_client.get_campaign_insights(
                                ad_account_id=report.meta_account_id,
                                since_date=prev_since,
                                until_date=prev_until,
                                campaign_ids=resolved_campaign_ids,
                                use_account_attribution_setting=getattr(meta_client, "use_account_attribution_setting", True)
                            )
                        except Exception as c_err:
                            logger.warning(f"Could not fetch prev campaign insights for {report.id} ({prev_since}..{prev_until}): {c_err}")
                            prev_camp_insights = None

                # Compute metrics
                metrics_data = ReportEngine.compute_aggregated_metrics(insight_data, campaign_insights=camp_insights)
                if should_compare and prev_insight_data is not None:
                    prev_metrics_data = ReportEngine.compute_aggregated_metrics(prev_insight_data, campaign_insights=prev_camp_insights)
                    deltas = ReportEngine.calculate_metrics_deltas(metrics_data, prev_metrics_data)
                    metrics_data["_deltas"] = deltas

                # Snapshot raw Meta response with fetched_at timestamp and attribution mode
                raw_meta_snapshot = {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "attribution_mode": "account" if getattr(meta_client, "use_account_attribution_setting", True) else "default",
                    "account_insight": insight_data,
                    "campaign_insights": camp_insights,
                }
                if should_compare and prev_insight_data is not None:
                    raw_meta_snapshot["prev_period"] = {
                        "account_insight": prev_insight_data,
                        "campaign_insights": prev_camp_insights,
                    }

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

            # Phase 1: Record RunHistory with status="sending" for non-test runs
            now_utc = datetime.now(timezone.utc)
            history = None
            if not is_test:
                history = RunHistory(
                    report_id=report.id,
                    user_id=report.user_id,
                    run_at=now_utc,
                    period_type=report.periodicity,
                    period_start=since_date,
                    period_end=until_date,
                    is_test=False,
                    status="sending",
                    metrics_data=metrics_data,
                    raw_meta_snapshot=raw_meta_snapshot
                )
                try:
                    session.add(history)
                    await session.commit()
                except IntegrityError as ie:
                    await session.rollback()
                    logger.warning(
                        f"IntegrityError (duplicate key) while recording 'sending' state for report {report.id} "
                        f"({since_date}..{until_date}): {ie}"
                    )
                    return {
                        "status": "skipped",
                        "message": "Duplicate run detected via unique constraint in sending state"
                    }

            # Deliver to Destinations
            tg_delivered = False
            tg_error = None
            sheets_delivered = False
            sheets_error = None
            recorded_telegram_message_id: int | None = None

            for dest in report.destinations:
                if not dest.is_enabled:
                    continue

                if dest.destination_type == "telegram":
                    if dest.is_connected and dest.telegram_chat_id:
                        try:
                            # 1. Main clean report message (without deltas)
                            detected_type = None
                            goals = [str(g).upper() for g in (report.campaign_filter_goals or [])]
                            if any("LEAD" in g for g in goals):
                                detected_type = "lead_generation"
                            elif any("MESSAGE" in g for g in goals):
                                detected_type = "direct_messages"
                            elif any("AWARENESS" in g or "REACH" in g for g in goals):
                                detected_type = "brand_awareness"

                            prev_info = (prev_since, prev_until) if (should_compare and prev_since and prev_until) else None
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
                                template_type=detected_type,
                                is_test=is_test,
                                account_timezone=report.account_timezone,
                                deltas=None,
                                prev_period_info=prev_info
                            )
                            sent_main = await telegram_sender.send_message(
                                chat_id=dest.telegram_chat_id,
                                text=msg_text,
                                message_thread_id=dest.telegram_thread_id
                            )
                            tg_msg_id = getattr(sent_main, "message_id", None) if not isinstance(sent_main, bool) else None
                            if tg_msg_id is not None:
                                recorded_telegram_message_id = tg_msg_id
                                if history:
                                    history.telegram_message_id = tg_msg_id

                            # 2. Separate comparison message ("was -> became") if should_compare
                            if should_compare and prev_insight_data is not None and deltas:
                                comp_msg = ReportEngine.build_comparison_message(
                                    report_name=report.name,
                                    account_name=report.meta_account_name,
                                    currency=report.currency,
                                    periodicity=report.periodicity,
                                    curr_since=since_date,
                                    curr_until=until_date,
                                    prev_since=prev_since,
                                    prev_until=prev_until,
                                    selected_metrics=report.metrics or [],
                                    curr_metric_values=metrics_data,
                                    prev_metric_values=prev_metrics_data,
                                    deltas=deltas,
                                    custom_labels=report.metric_labels or {},
                                    lang=report.metric_lang or "ru",
                                    account_timezone=report.account_timezone
                                )
                                await telegram_sender.send_message(
                                    chat_id=dest.telegram_chat_id,
                                    text=comp_msg,
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
                                lang=report.metric_lang or "ru",
                                deltas=deltas
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

            # Determine overall run status: distinct "no_data" (нет расхода) vs "failed" (сбой)
            has_no_data = (metrics_data.get("spend") or 0.0) == 0.0 and (metrics_data.get("impressions") or 0) == 0
            if tg_error or sheets_error:
                run_status = "partial" if (tg_delivered or sheets_delivered) else "failed"
            elif has_no_data:
                run_status = "no_data"
            else:
                run_status = "success"

            duration = round(time.time() - start_time, 2)
            now_utc = datetime.now(timezone.utc)
            error_msg_full = f"{tg_error or ''} {sheets_error or ''}".strip() or None

            # Phase 2: Update RunHistory from "sending" to final status (or create record for test runs)
            try:
                if not is_test and history:
                    history.status = run_status
                    history.duration_seconds = duration
                    history.telegram_delivered = tg_delivered
                    if recorded_telegram_message_id is not None:
                        history.telegram_message_id = recorded_telegram_message_id
                    history.telegram_error = tg_error
                    history.sheets_delivered = sheets_delivered
                    history.sheets_error = sheets_error
                    history.error_message = error_msg_full
                    history.raw_meta_snapshot = raw_meta_snapshot
                else:
                    history = RunHistory(
                        report_id=report.id,
                        user_id=report.user_id,
                        run_at=now_utc,
                        period_type=report.periodicity,
                        period_start=since_date,
                        period_end=until_date,
                        is_test=is_test,
                        status=run_status,
                        duration_seconds=duration,
                        metrics_data=metrics_data,
                        raw_meta_snapshot=raw_meta_snapshot,
                        telegram_delivered=tg_delivered,
                        telegram_message_id=recorded_telegram_message_id,
                        telegram_error=tg_error,
                        sheets_delivered=sheets_delivered,
                        sheets_error=sheets_error,
                        error_message=error_msg_full
                    )
                    session.add(history)

                # Update report status and next_run_at
                report.last_run_at = now_utc
                report.last_run_status = run_status
                report.last_run_error = error_msg_full

                if not is_test:
                    # Schedule subsequent run
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
            except IntegrityError as ie:
                await session.rollback()
                logger.warning(
                    f"IntegrityError committing final status for report {report.id} "
                    f"({since_date}..{until_date}, is_test={is_test}): {ie}"
                )
                if not is_test:
                    return {
                        "status": "skipped",
                        "message": "Duplicate run detected via unique constraint",
                        "telegram_delivered": tg_delivered,
                        "sheets_delivered": sheets_delivered
                    }
                return {
                    "status": run_status,
                    "duration_seconds": duration,
                    "metrics": metrics_data,
                    "telegram_delivered": tg_delivered,
                    "sheets_delivered": sheets_delivered,
                    "warning": "History record could not be saved due to DB constraint"
                }
            except Exception as db_exc:
                await session.rollback()
                logger.error(f"Database error committing RunHistory for report {report.id}: {db_exc}", exc_info=True)
                return {
                    "status": run_status if (tg_delivered or sheets_delivered) else "failed",
                    "duration_seconds": duration,
                    "metrics": metrics_data,
                    "telegram_delivered": tg_delivered,
                    "sheets_delivered": sheets_delivered,
                    "warning": f"Database commit failed: {db_exc}"
                }

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
    async def check_all_meta_tokens():
        """
        Daily background health check for Meta tokens.
        Validates token via client.verify_token().
        If expired, marks is_valid=False and sends alert to Telegram ONCE (without repeated spam).
        """
        async with AsyncSessionLocal() as session:
            try:
                now_utc = datetime.now(timezone.utc)
                query = select(MetaConnection).where(MetaConnection.encrypted_access_token != None)
                result = await session.execute(query)
                conns = result.scalars().all()

                for conn in conns:
                    if conn.last_verified_at:
                        last_v = conn.last_verified_at if conn.last_verified_at.tzinfo else conn.last_verified_at.replace(tzinfo=timezone.utc)
                        if (now_utc - last_v) < timedelta(hours=24):
                            continue

                    try:
                        token = decrypt_secret(conn.encrypted_access_token)
                        client = MetaClient(access_token=token)
                        await client.verify_token()
                        conn.is_valid = True
                        conn.last_verified_at = now_utc
                    except MetaTokenExpiredError as exc:
                        was_valid = conn.is_valid
                        conn.is_valid = False
                        conn.last_verified_at = now_utc

                        # Send alert to Telegram ONLY IF the connection was previously valid (transition to invalid)
                        # This guarantees exactly 1 alert is sent, avoiding spamming the user repeatedly.
                        if was_valid:
                            logger.warning(f"Meta token for user {conn.user_id} expired during daily health check: {exc}")
                            dest_query = (
                                select(Destination)
                                .join(Report, Destination.report_id == Report.id)
                                .where(
                                    Report.user_id == conn.user_id,
                                    Destination.destination_type == "telegram",
                                    Destination.is_connected == True,
                                    Destination.telegram_chat_id != None
                                )
                            )
                            dest_res = await session.execute(dest_query)
                            destinations = dest_res.scalars().all()
                            for d in destinations:
                                try:
                                    await telegram_sender.send_token_expired_alert(
                                        chat_id=d.telegram_chat_id,
                                        report_name="AdPulse Account",
                                        message_thread_id=d.telegram_thread_id
                                    )
                                except Exception as alert_err:
                                    logger.error(f"Failed to send token expiration alert to Telegram: {alert_err}")

                    except Exception as err:
                        logger.warning(f"Transient error verifying token for user {conn.user_id}: {err}")

                await session.commit()
            except Exception as e:
                logger.error(f"Error during check_all_meta_tokens: {e}", exc_info=True)

    @staticmethod
    async def cleanup_old_raw_snapshots(days: int = 90) -> int:
        """
        Cleans up raw_meta_snapshot in RunHistory records older than `days` days.
        Preserves metrics_data, telegram_message_id, duration, and status for historical analytics,
        while releasing JSON storage for expired raw API payloads.
        Returns the number of records updated.
        """
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(RunHistory)
                    .where(
                        RunHistory.run_at < cutoff_dt,
                        RunHistory.raw_meta_snapshot != None  # noqa: E711
                    )
                    .values(raw_meta_snapshot=None)
                )
                res = await session.execute(stmt)
                await session.commit()
                count = res.rowcount
                if count > 0:
                    logger.info(f"Cleaned up raw_meta_snapshot for {count} RunHistory records older than {days} days")
                return count
        except Exception as e:
            logger.error(f"Error during cleanup_old_raw_snapshots: {e}", exc_info=True)
            return 0

    @staticmethod
    async def run_worker_loop():
        """Continuous polling worker loop that fires scheduled reports and runs daily token checks and snapshot cleanup."""
        logger.info("Scheduler worker loop started.")
        last_token_check_at: datetime | None = None
        last_cleanup_at: datetime | None = None
        while True:
            try:
                now_utc = datetime.now(timezone.utc)

                # Daily Meta token health check
                if last_token_check_at is None or (now_utc - last_token_check_at) >= timedelta(hours=24):
                    await SchedulerService.check_all_meta_tokens()
                    last_token_check_at = now_utc

                # Daily cleanup of raw_meta_snapshot older than 90 days
                if last_cleanup_at is None or (now_utc - last_cleanup_at) >= timedelta(hours=24):
                    await SchedulerService.cleanup_old_raw_snapshots(days=90)
                    last_cleanup_at = now_utc

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
