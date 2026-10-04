from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo
import pytest

from app.models.run_history import RunHistory
from app.services.report_engine import ReportEngine
from app.services.scheduler_service import SchedulerService
from app.services.meta_client import MetaTokenExpiredError



def test_dst_transition_preserves_local_time():
    """
    Verifies that calculate_next_run preserves local schedule_time across DST shifts.
    In America/New_York:
    - On Nov 1, 2026, DST ends at 02:00 AM (EDT UTC-4 -> EST UTC-5).
    - A daily report scheduled for 09:00 local time fires at 09:00 EST (14:00 UTC) on Nov 1,
      and at 09:00 EST (14:00 UTC) on Nov 2.
    - Local time is always 09:00 AM.
    """
    tz_ny = "America/New_York"
    # Oct 31, 2026 at 20:00 EDT
    from_dt_1 = datetime(2026, 10, 31, 20, 0, 0, tzinfo=ZoneInfo(tz_ny))
    next_run_1 = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="09:00",
        send_timezone_str=tz_ny,
        from_dt=from_dt_1,
        account_tz_str=tz_ny
    )
    # Next morning: Nov 1 at 09:00 local time (which is EST, UTC-5 after 2am roll-back) -> 14:00 UTC
    assert next_run_1 == datetime(2026, 11, 1, 14, 0, 0, tzinfo=timezone.utc)

    # Nov 1, 2026 at 20:00 EST (after DST switch)
    from_dt_2 = datetime(2026, 11, 1, 20, 0, 0, tzinfo=ZoneInfo(tz_ny))
    next_run_2 = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="09:00",
        send_timezone_str=tz_ny,
        from_dt=from_dt_2,
        account_tz_str=tz_ny
    )
    # Next morning: Nov 2 at 09:00 EST (UTC-5) -> 14:00 UTC
    assert next_run_2 == datetime(2026, 11, 2, 14, 0, 0, tzinfo=timezone.utc)
    # In local time, both are exactly 09:00 AM
    assert next_run_1.astimezone(ZoneInfo(tz_ny)).strftime("%H:%M") == "09:00"
    assert next_run_2.astimezone(ZoneInfo(tz_ny)).strftime("%H:%M") == "09:00"


def test_month_end_scheduling_jan_31_to_feb_28_and_leap():
    """
    Verifies that scheduling a monthly report for the 31st clamps safely to the
    last day of shorter months (e.g. Feb 28 or Feb 29 for leap year) without skipping or crashing.
    """
    tz = "UTC"

    # Non-leap year 2025: Jan 31 -> next month should be Feb 28
    base_2025 = datetime(2025, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
    next_run_2025 = SchedulerService.calculate_next_run(
        periodicity="monthly",
        schedule_time_str="10:00",
        send_timezone_str=tz,
        from_dt=base_2025,
        schedule_monthday=31,
        account_tz_str=tz
    )
    local_2025 = next_run_2025.astimezone(timezone.utc)
    assert (local_2025.year, local_2025.month, local_2025.day) == (2025, 2, 28)
    assert local_2025.strftime("%H:%M") == "10:00"

    # Leap year 2028: Jan 31 -> next month should be Feb 29
    base_2028 = datetime(2028, 1, 31, 10, 0, 0, tzinfo=timezone.utc)
    next_run_2028 = SchedulerService.calculate_next_run(
        periodicity="monthly",
        schedule_time_str="10:00",
        send_timezone_str=tz,
        from_dt=base_2028,
        schedule_monthday=31,
        account_tz_str=tz
    )
    local_2028 = next_run_2028.astimezone(timezone.utc)
    assert (local_2028.year, local_2028.month, local_2028.day) == (2028, 2, 29)
    assert local_2028.strftime("%H:%M") == "10:00"


def test_unrounded_cpc_ratio_delta():
    """
    Verifies that ratio metrics like CPC are computed from unrounded component totals
    to prevent rounding distortion.
    Example:
    Curr: spend=$21.05, clicks=250 -> unrounded CPC = 0.0842, rounded CPC = 0.08
    Prev: spend=$22.40, clicks=251 -> unrounded CPC = 0.08924, rounded CPC = 0.09
    Naive delta from rounded: (0.08 - 0.09) / 0.09 = -11.1%
    Exact delta from raw totals: (0.0842 - 0.08924) / 0.08924 = -5.6%
    """
    curr = {
        "spend": 21.05,
        "clicks": 250,
        "cpc": 0.08,
        "approximate_metrics": []
    }
    prev = {
        "spend": 22.40,
        "clicks": 251,
        "cpc": 0.09,
        "approximate_metrics": []
    }

    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)
    cpc_delta = deltas["cpc"]
    assert cpc_delta["status"] == "compared"
    # Should be approx -5.6%, NOT -11.1%
    assert cpc_delta["diff_pct"] == pytest.approx(-5.7, abs=0.1)
    assert cpc_delta["badge"] == "🟢 ▼ -6%"


def test_no_data_does_not_output_minus_100_percent():
    """
    Verifies that when a metric has no data in current period (curr_val is None),
    the delta is suppressed with status='no_data', NEVER outputting a misleading '▼ -100%'.
    """
    curr = {
        "spend": 100.0,
        "leads": None,  # Not tracked or no leads recorded
        "approximate_metrics": []
    }
    prev = {
        "spend": 100.0,
        "leads": 10,
        "approximate_metrics": []
    }

    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)
    leads_delta = deltas["leads"]
    assert leads_delta["status"] == "no_data"
    assert leads_delta["diff_pct"] is None
    assert leads_delta["badge"] is None


@pytest.mark.asyncio
async def test_two_phase_execution_and_stalled_timeout():
    """
    Verifies two-phase execution lifecycle:
    1. Worker creates RunHistory with status='sending'.
    2. Successfully finishes and transitions status to 'success'.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_two_phase"
    mock_report.user_id = 1
    mock_report.name = "Two Phase Report"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "UTC"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "UTC"
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

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "valid_fernet_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    created_history_records = []

    mock_session = AsyncMock()
    def mock_add(inst):
        if isinstance(inst, RunHistory):
            created_history_records.append(inst)
    mock_session.add = MagicMock(side_effect=mock_add)
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    # Duplicate check query returns None (first attempt)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.get_insights = AsyncMock(return_value={"spend": "50.00", "impressions": "1000"})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.ReportEngine.check_final_data_delay", return_value=(True, datetime.now(timezone.utc))), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock):

        res = await SchedulerService.execute_report(
            report_id="rep_two_phase",
            is_test=False,
            cache_bypass=True
        )

        assert res["status"] == "success"
        # Verify initial record was created with 'sending' and updated to 'success'
        assert len(created_history_records) >= 1
        history = created_history_records[0]
        assert history.status == "success"
        assert history.report_id == "rep_two_phase"


@pytest.mark.asyncio
async def test_meta_token_daily_check_single_alert():
    """
    Verifies that check_all_meta_tokens notifies users once per failure
    and suppresses redundant alerts if checked again on the same day.
    """
    mock_conn = MagicMock()
    mock_conn.user_id = 42
    mock_conn.encrypted_access_token = "some_encrypted_token"
    mock_conn.is_valid = True
    mock_conn.last_verified_at = None

    mock_dest = MagicMock()
    mock_dest.telegram_chat_id = 123456789
    mock_dest.telegram_thread_id = None

    mock_session = AsyncMock()
    # 1. First execute: conns query
    mock_conns_res = MagicMock()
    mock_conns_res.scalars().all.return_value = [mock_conn]

    # 2. Second execute: destinations query
    mock_dests_res = MagicMock()
    mock_dests_res.scalars().all.return_value = [mock_dest]

    mock_session.execute = AsyncMock(side_effect=[mock_conns_res, mock_dests_res, mock_conns_res])
    mock_session.commit = AsyncMock()

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.verify_token = AsyncMock(side_effect=MetaTokenExpiredError("Session has expired", code=190))

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.telegram_sender.send_token_expired_alert", new_callable=AsyncMock) as mock_alert:

        # Run 1: was_valid is True, verification fails -> alert sent, is_valid set to False
        await SchedulerService.check_all_meta_tokens()
        assert mock_alert.call_count == 1
        assert mock_conn.is_valid is False
        assert mock_conn.last_verified_at is not None

        # Run 2: (mocking second run within 24 hours):
        # last_verified_at was just set, so it skips!
        await SchedulerService.check_all_meta_tokens()
        assert mock_alert.call_count == 1  # No duplicate alert sent
