import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.services.scheduler_service import SchedulerService

def test_scheduler_calculate_next_run_daily():
    tz = ZoneInfo("Asia/Tashkent")
    base_dt = datetime(2026, 9, 29, 6, 0, 0, tzinfo=tz)

    next_run = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="08:00",
        send_timezone_str="Asia/Tashkent",
        from_dt=base_dt,
        account_tz_str="Asia/Tashkent"
    )

    # In Tashkent, period ended Sep 28 23:59:59. Delay of 6 hours is Sep 29 05:59:59.
    # Scheduled for 08:00 Sep 29 (> 05:59:59), so it should fire at 08:00 Tashkent time (03:00 UTC)
    expected_local = datetime(2026, 9, 29, 8, 0, 0, tzinfo=tz)
    assert next_run == expected_local.astimezone(timezone.utc)

def test_scheduler_enforces_final_data_delay():
    tz = ZoneInfo("Asia/Tashkent")
    base_dt = datetime(2026, 9, 29, 1, 0, 0, tzinfo=tz)

    # Scheduled for 02:00 (only 2 hours after midnight). 6-hour delay requires waiting until 06:00!
    next_run = SchedulerService.calculate_next_run(
        periodicity="daily",
        schedule_time_str="02:00",
        send_timezone_str="Asia/Tashkent",
        from_dt=base_dt,
        account_tz_str="Asia/Tashkent"
    )

    # Must be deferred to at least 06:00 Tashkent time
    min_ready_local = datetime(2026, 9, 29, 5, 59, 59, tzinfo=tz)
    assert next_run >= min_ready_local.astimezone(timezone.utc)
