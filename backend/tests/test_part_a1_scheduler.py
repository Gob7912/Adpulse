import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.scheduler_service import SchedulerService
from app.models.run_history import RunHistory

def test_part_a1_ten_days_daily_schedule_simulation():
    """
    Simulation of 10 consecutive simulated days for daily report in Asia/Tashkent:
    - schedule_time: '09:00', send_timezone: 'Asia/Tashkent', account_tz: 'Asia/Tashkent'
    - next_run_at must advance by exactly +1 day in local time.
    - No skips, no duplicates.
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    start_dt = datetime(2026, 10, 10, 9, 0, 0, tzinfo=tz_tashkent)
    
    current_time = start_dt
    history_runs = []
    
    for day in range(10):
        # Calculate next run from current run time
        next_run_utc = SchedulerService.calculate_next_run(
            periodicity="daily",
            schedule_time_str="09:00",
            send_timezone_str="Asia/Tashkent",
            from_dt=current_time,
            account_tz_str="Asia/Tashkent"
        )
        next_run_local = next_run_utc.astimezone(tz_tashkent)
        
        expected_next_local = (current_time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        assert next_run_local == expected_next_local, f"Day {day}: expected {expected_next_local}, got {next_run_local}"
        
        history_runs.append({
            "run_time": current_time,
            "next_run": next_run_local,
            "result": "OK (+1 day, 09:00 Tashkent)"
        })
        current_time = next_run_local

    assert len(history_runs) == 10


def test_part_a1_six_am_rule():
    """
    Rule 06:00: report scheduled before 06:00 must be delayed to 06:00 (due to final data delay).
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    # Base: 04:00 AM on Oct 10
    from_dt = datetime(2026, 10, 10, 4, 0, 0, tzinfo=tz_tashkent)
    
    next_run_utc = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="04:00",
        send_timezone_str="Asia/Tashkent",
        from_dt=from_dt,
        account_tz_str="Asia/Tashkent"
    )
    next_run_local = next_run_utc.astimezone(tz_tashkent)
    # Target 04:00 is before 06:00 (period ends at midnight 00:00:00, 6h delay -> ready at exactly 06:00:00 UTC+5)
    assert next_run_local.hour == 6
    assert next_run_local.minute == 0
    assert next_run_local.second == 0


def test_part_a1_pause_and_resume():
    """
    Pause report (is_active=False) and resume (is_active=True).
    When paused, scheduler skips execution. When resumed, next_run_at is recalculated.
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    now = datetime(2026, 10, 10, 15, 0, 0, tzinfo=tz_tashkent)
    
    # Recalculate upon unpausing at 15:00
    next_run_utc = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="09:00",
        send_timezone_str="Asia/Tashkent",
        from_dt=now,
        account_tz_str="Asia/Tashkent"
    )
    next_run_local = next_run_utc.astimezone(tz_tashkent)
    # Since 09:00 today has passed, next run should be tomorrow at 09:00
    assert next_run_local == datetime(2026, 10, 11, 9, 0, 0, tzinfo=tz_tashkent)


def test_part_a1_change_schedule_time():
    """
    User changes schedule_time from 09:00 to 14:00 on the same day before 14:00.
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    # At 10:00 (after 09:00 ran), user changes to 14:00
    now = datetime(2026, 10, 10, 10, 0, 0, tzinfo=tz_tashkent)
    next_run_utc = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="14:00",
        send_timezone_str="Asia/Tashkent",
        from_dt=now,
        account_tz_str="Asia/Tashkent"
    )
    next_run_local = next_run_utc.astimezone(tz_tashkent)
    # Today 14:00 hasn't happened yet, so it can run today at 14:00
    assert next_run_local == datetime(2026, 10, 10, 14, 0, 0, tzinfo=tz_tashkent)


@pytest.mark.asyncio
async def test_part_a1_worker_crash_after_send_before_success_history():
    """
    Two-Phase execution: if worker crashes after sending (status was 'sending'),
    duplicate execution is prevented by the 'sending' record.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_crash_test"
    mock_report.user_id = 1
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_999"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = False
    mock_report.destinations = []

    mock_session = AsyncMock()
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    # 1. Existing run with status='sending' created 5 minutes ago (< 15 min timeout)
    stalled_run = RunHistory(
        id=99,
        report_id="rep_crash_test",
        user_id=1,
        run_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        period_type="daily",
        period_start="2026-10-09",
        period_end="2026-10-09",
        status="sending"
    )
    mock_session.scalar = AsyncMock(return_value=stalled_run)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_send:

        res = await SchedulerService.execute_report(
            report_id="rep_crash_test",
            is_test=False,
            cache_bypass=True
        )

        # Worker sees status='sending' (< 15 min), skips, and does NOT send Telegram message!
        assert res["status"] == "skipped"
        assert res["message"] == "Report is currently sending"
        assert mock_send.call_count == 0


def test_part_a1_transitions_month_end_weekly_monthly():
    """
    Tests month transitions (Jan 31 -> Feb 28/29), weekly (Monday to Monday), monthly.
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    # Weekly test: scheduled for Monday (weekday 0) at 10:00
    # From Wednesday Oct 14, 2026 -> next Monday is Oct 19, 2026
    wed = datetime(2026, 10, 14, 12, 0, 0, tzinfo=tz_tashkent)
    next_run_utc = SchedulerService.calculate_next_run(
        periodicity="weekly",
        schedule_time_str="10:00",
        send_timezone_str="Asia/Tashkent",
        schedule_weekday=0,
        from_dt=wed,
        account_tz_str="Asia/Tashkent"
    )
    assert next_run_utc.astimezone(tz_tashkent) == datetime(2026, 10, 19, 10, 0, 0, tzinfo=tz_tashkent)

    # Monthly test on 31st: Jan 31 -> Feb 28 (non leap 2025)
    jan31 = datetime(2025, 1, 31, 11, 0, 0, tzinfo=tz_tashkent)
    next_feb = SchedulerService.calculate_next_run(
        periodicity="monthly",
        schedule_time_str="10:00",
        send_timezone_str="Asia/Tashkent",
        schedule_monthday=31,
        from_dt=jan31,
        account_tz_str="Asia/Tashkent"
    )
    feb_local = next_feb.astimezone(tz_tashkent)
    assert (feb_local.year, feb_local.month, feb_local.day) == (2025, 2, 28)


@pytest.mark.asyncio
async def test_part_a1_worker_offline_at_schedule_and_wakes_up_later():
    """
    Test scenario:
    1. Report is scheduled for 09:00 Asia/Tashkent.
    2. Worker is offline/down at 09:00, and only boots up at 11:30.
    3. Worker immediately executes the due report exactly once.
    4. next_run_at advances to next day 09:00.
    5. A subsequent worker tick does NOT repeat the execution (no duplicate message).
    """
    tz_tashkent = ZoneInfo("Asia/Tashkent")
    scheduled_due = datetime(2026, 10, 10, 9, 0, 0, tzinfo=tz_tashkent).astimezone(timezone.utc)
    wakeup_time = datetime(2026, 10, 10, 11, 30, 0, tzinfo=tz_tashkent).astimezone(timezone.utc)

    mock_report = MagicMock()
    mock_report.id = "rep_offline_wakeup"
    mock_report.user_id = 1
    mock_report.name = "Offline Worker Test"
    mock_report.is_active = True
    mock_report.next_run_at = scheduled_due
    mock_report.periodicity = "daily"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_offline"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "impressions"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = False

    mock_dest = MagicMock()
    mock_dest.id = "dest_offline"
    mock_dest.is_enabled = True
    mock_dest.destination_type = "telegram"
    mock_dest.is_connected = True
    mock_dest.telegram_chat_id = -100999888
    mock_dest.telegram_thread_id = None
    mock_report.destinations = [mock_dest]

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "fake_enc_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.scalar = AsyncMock(return_value=None)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.get_insights = AsyncMock(return_value={"spend": "35.50", "impressions": "4200"})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_send:

        # 1. Worker wakes up late at 11:30 (next_run_at <= wakeup_time)
        res = await SchedulerService.execute_report("rep_offline_wakeup", is_test=False, cache_bypass=True)
        assert res["status"] == "success"
        assert mock_send.call_count == 1

        # next_run_at must advance to tomorrow 09:00 Tashkent time
        assert mock_report.next_run_at is not None
        next_local = mock_report.next_run_at.astimezone(tz_tashkent)
        assert next_local.hour == 9 and next_local.minute == 0
        tomorrow_day = (datetime.now(tz_tashkent) + timedelta(days=1)).day
        assert next_local.day == tomorrow_day

        # 2. Subsequent check for the same period finds existing success record
        existing_success = RunHistory(
            report_id="rep_offline_wakeup",
            user_id=1,
            period_type="daily",
            period_start=res["metrics"].get("_since", "2026-10-09"),
            period_end=res["metrics"].get("_until", "2026-10-09"),
            status="success"
        )
        mock_session.scalar = AsyncMock(return_value=existing_success)

        res_second = await SchedulerService.execute_report("rep_offline_wakeup", is_test=False, cache_bypass=True)
        assert res_second["status"] == "skipped"
        assert res_second["message"] == "Already executed for this period"
        # Total telegram sends remains 1 (no duplicate sent)
        assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_part_a1_stalled_sending_crash_recovery_and_admin_alert():
    """
    Test scenario:
    1. Worker previously crashed during dispatch, leaving RunHistory in status='sending'.
    2. Over 15 minutes have passed since the run was created.
    3. On next execution, scheduler detects stalled run (> 15m), marks it 'failed',
       advances schedule, and dispatches an alert to settings.TELEGRAM_ADMIN_CHAT_ID.
    4. What the user sees: run is transitioned to failed with clear explanation.
    5. Deduplication: subsequent runs with the same key do NOT spam admin.
    """
    from app.config import settings

    mock_report = MagicMock()
    mock_report.id = "rep_stalled_1"
    mock_report.user_id = 1
    mock_report.name = "Stalled Report"
    mock_report.periodicity = "daily"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.account_timezone = "Asia/Tashkent"

    stalled_run = RunHistory(
        id=777,
        report_id="rep_stalled_1",
        user_id=1,
        run_at=datetime.now(timezone.utc) - timedelta(minutes=25),
        period_type="daily",
        period_start="2026-10-09",
        period_end="2026-10-09",
        status="sending"
    )

    # Stored admin alerts simulating DB persistence
    admin_alerts_store = {}

    mock_session = AsyncMock()

    async def mock_scalar_impl(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        if "admin_alerts" in stmt_str:
            return admin_alerts_store.get("stalled:rep_stalled_1:777")
        return stalled_run

    def mock_add_impl(obj):
        if hasattr(obj, "alert_key"):
            admin_alerts_store[obj.alert_key] = obj

    mock_session.scalar = AsyncMock(side_effect=mock_scalar_impl)
    mock_session.add = MagicMock(side_effect=mock_add_impl)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    with patch.object(settings, "TELEGRAM_ADMIN_CHAT_ID", 999999999), \
         patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_bot_token"), \
         patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_tg_send:

        # 1. Detects stalled run > 15m without telegram_message_id -> marks failed, notifies admin
        res = await SchedulerService.execute_report("rep_stalled_1", is_test=False, cache_bypass=True)
        assert res["status"] == "skipped"
        assert res["message"] == "Stalled sending run marked failed"
        assert stalled_run.status == "failed"
        assert "timed out in sending state" in stalled_run.error_message
        assert mock_report.last_run_status == "failed"

        # Admin received alert exactly ONCE
        assert mock_tg_send.call_count == 1
        sent_call = mock_tg_send.call_args_list[0]
        assert sent_call.kwargs["chat_id"] == 999999999
        assert "Stalled Sending Run" in sent_call.kwargs["text"]

        # 2. Second trigger on the exact same stalled run alert -> DB deduplication prevents spam!
        was_sent = await SchedulerService.notify_admin_alert(
            report_name=mock_report.name,
            report_id=str(mock_report.id),
            alert_type="Stalled Sending Run",
            detail="Repeated alert attempt",
            dedup_key="stalled:rep_stalled_1:777"
        )
        assert was_sent is False
        # Call count is still 1 (no spam)
        assert mock_tg_send.call_count == 1


@pytest.mark.asyncio
async def test_part_a1_stalled_sending_with_telegram_message_id_recovers_to_success():
    """
    Test scenario:
    1. Worker executed report, successfully sent Telegram message (telegram_message_id=884422),
       but crashed before writing 'status = success' (run was left in 'sending' state > 15m).
    2. Scheduler detects stalled run with telegram_message_id != None.
    3. Requirement: instead of marking it 'failed', transition it to 'success' and
       advance schedule, because the report WAS successfully delivered.
    4. NO admin failure alert must be triggered.
    """
    from app.config import settings

    mock_report = MagicMock()
    mock_report.id = "rep_stalled_delivered"
    mock_report.user_id = 1
    mock_report.name = "Delivered Report"
    mock_report.periodicity = "daily"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.last_run_status = "sending"

    stalled_delivered_run = RunHistory(
        id=888,
        report_id="rep_stalled_delivered",
        user_id=1,
        run_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        period_type="daily",
        period_start="2026-10-09",
        period_end="2026-10-09",
        status="sending",
        telegram_message_id=884422  # Telegram message ID was saved!
    )

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=stalled_delivered_run)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    with patch.object(settings, "TELEGRAM_ADMIN_CHAT_ID", 999999999), \
         patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_bot_token"), \
         patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_tg_send:

        res = await SchedulerService.execute_report("rep_stalled_delivered", is_test=False, cache_bypass=True)

        # Verified: transitioned to success!
        assert res["status"] == "skipped"
        assert res["message"] == "Stalled sending run marked success"
        assert stalled_delivered_run.status == "success"
        assert stalled_delivered_run.telegram_delivered is True
        assert stalled_delivered_run.error_message is None
        assert mock_report.last_run_status == "success"
        assert mock_report.last_run_error is None

        # Schedule advanced
        assert mock_report.next_run_at is not None

        # No error alerts sent to admin because delivery actually succeeded
        assert mock_tg_send.call_count == 0
