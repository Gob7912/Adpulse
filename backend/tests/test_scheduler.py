from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

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


@pytest.mark.asyncio
async def test_scheduler_duplicate_prevention():
    """
    Ensures that when a successful non-test run already exists for the calculated
    period (report_id, period_start, period_end, is_test=False), execution is skipped,
    preventing duplicate Telegram messages and Google Sheets rows.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_101"
    mock_report.user_id = 1
    mock_report.name = "Test Report"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.user = MagicMock()
    mock_report.destinations = []

    mock_existing_history = MagicMock()
    mock_existing_history.status = "success"
    mock_existing_history.is_test = False

    # Mock DB session
    mock_session = AsyncMock()
    # First query for cache returns None, second query for report returns mock_report
    # third scalar query for duplicate check returns mock_existing_history
    mock_session.execute = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=mock_existing_history)

    # For report loading
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute.return_value = mock_report_res

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_tg, \
         patch("app.services.scheduler_service.sheets_service.append_report_row", new_callable=AsyncMock) as mock_sheets:

        res = await SchedulerService.execute_report(
            report_id="rep_101",
            is_test=False,
            cache_bypass=True
        )

        assert res["status"] == "skipped"
        assert "Already executed" in res["message"]
        # Ensure no deliveries were triggered
        mock_tg.assert_not_called()
        mock_sheets.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_no_data_distinct_from_failed():
    """
    Verifies that when Meta API returns an empty insight row (no spend and no impressions),
    the run status is 'no_data' (нет расхода), distinctly different from 'failed' (сбой).
    """
    mock_report = MagicMock()
    mock_report.id = "rep_102"
    mock_report.user_id = 1
    mock_report.name = "Empty Insight Report"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_123"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "impressions"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = False
    mock_report.destinations = []

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "valid_encrypted_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.scalar = AsyncMock(return_value=None)  # No duplicate run exists

    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute.return_value = mock_report_res

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    # Meta returns empty insights: {}
    mock_client.get_insights = AsyncMock(return_value={})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"):

        res = await SchedulerService.execute_report(
            report_id="rep_102",
            is_test=False,
            cache_bypass=True
        )

        assert res["status"] == "no_data"
        assert mock_report.last_run_status == "no_data"


@pytest.mark.asyncio
async def test_consecutive_test_runs_then_scheduled_run():
    """
    Scenario:
    1. First test run (is_test=True) for today succeeds.
    2. Second test run (is_test=True) for today succeeds immediately without blocking or index conflict.
    3. Scheduled run (is_test=False) for the same period is NOT blocked by the test runs and succeeds.
    4. Subsequent scheduled run (is_test=False) for the same period is detected as duplicate and skipped.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_flow_1"
    mock_report.user_id = 1
    mock_report.name = "Flow Test Report"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_999"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "impressions"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = False
    mock_report.destinations = []

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "enc_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    # In-memory history store to emulate DB state across calls
    stored_histories = []

    mock_session = AsyncMock()

    def mock_add(obj):
        stored_histories.append(obj)

    mock_session.add = mock_add

    async def mock_scalar(query):
        # Emulate duplicate check query: RunHistory.is_test == False and status in ("success", "no_data")
        # Check if any non-test successful history exists in stored_histories
        for h in stored_histories:
            if not getattr(h, "is_test", False) and getattr(h, "status", "") in ("success", "no_data"):
                return h
        return None

    mock_session.scalar = mock_scalar

    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.get_insights = AsyncMock(return_value={"spend": "25.00", "impressions": "1000"})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"):

        # 1. First test run
        res_test1 = await SchedulerService.execute_report("rep_flow_1", is_test=True, cache_bypass=True)
        assert res_test1["status"] == "success"
        assert len(stored_histories) == 1
        assert stored_histories[0].is_test is True

        # 2. Second test run immediately after
        res_test2 = await SchedulerService.execute_report("rep_flow_1", is_test=True, cache_bypass=True)
        assert res_test2["status"] == "success"
        assert len(stored_histories) == 2
        assert stored_histories[1].is_test is True

        # 3. Scheduled run for the period (is_test=False)
        res_sched1 = await SchedulerService.execute_report("rep_flow_1", is_test=False, cache_bypass=True)
        assert res_sched1["status"] == "success"
        assert len(stored_histories) == 3
        assert stored_histories[2].is_test is False

        # 4. Second scheduled run for same period -> must be skipped
        res_sched2 = await SchedulerService.execute_report("rep_flow_1", is_test=False, cache_bypass=True)
        assert res_sched2["status"] == "skipped"
        assert "Already executed" in res_sched2["message"]
        # History count does not increase because it was skipped before inserting
        assert len(stored_histories) == 3


@pytest.mark.asyncio
async def test_scheduler_pipeline_show_comparison_toggle():
    """
    Verifies that when show_comparison=True (and not is_test), get_multi_period_insights is invoked
    and deltas are computed and attached to metrics_data.
    When is_test=True or show_comparison=False, comparison is bypassed.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_comp_1"
    mock_report.user_id = 1
    mock_report.name = "Comparison Report"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "08:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_999"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "leads"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = True
    mock_report.destinations = []

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "enc_token"
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
    # Multi-period returns both current and previous insight rows
    mock_client.get_multi_period_insights = AsyncMock(return_value={
        ("2026-10-03", "2026-10-03"): {"spend": "100.00", "actions": [{"action_type": "lead", "value": "10"}]},
        ("2026-10-02", "2026-10-02"): {"spend": "80.00", "actions": [{"action_type": "lead", "value": "5"}]}
    })
    mock_client.get_insights = AsyncMock(return_value={"spend": "50.00", "impressions": "1000"})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"):

        # 1. Scheduled run with show_comparison=True
        res = await SchedulerService.execute_report("rep_comp_1", is_test=False, cache_bypass=True)
        assert res["status"] == "success"
        assert mock_client.get_multi_period_insights.called
        assert "_deltas" in res["metrics"]
        assert res["metrics"]["_deltas"]["spend"]["badge"] == "▲ +25%"
        assert res["metrics"]["_deltas"]["leads"]["badge"] == "🟢 ▲ +100%"

        # Reset call flag
        mock_client.get_multi_period_insights.reset_mock()
        mock_client.get_insights.reset_mock()

        # 2. Test run (is_test=True): should NOT call get_multi_period_insights
        res_test = await SchedulerService.execute_report("rep_comp_1", is_test=True, cache_bypass=True)
        assert res_test["status"] == "success"
        assert not mock_client.get_multi_period_insights.called
        assert mock_client.get_insights.called
        assert "_deltas" not in res_test["metrics"]


@pytest.mark.asyncio
async def test_scheduler_telegram_message_id_and_raw_snapshot_saved():
    """
    Verifies that when profile_visits is selected:
    1. Campaign insights are queried for both periods (curr and prev).
    2. telegram_message_id is extracted and saved to RunHistory upon dispatch.
    3. raw_meta_snapshot is recorded with fetched_at, attribution_mode, and insight data.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_snap_1"
    mock_report.user_id = 1
    mock_report.name = "Snapshot Test"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_777"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "impressions", "profile_visits"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = True

    mock_dest = MagicMock()
    mock_dest.id = "dest_1"
    mock_dest.is_enabled = True
    mock_dest.destination_type = "telegram"
    mock_dest.is_connected = True
    mock_dest.telegram_chat_id = -10012345
    mock_dest.telegram_thread_id = None
    mock_report.destinations = [mock_dest]

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "enc_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    stored_histories = []
    mock_session = AsyncMock()
    mock_session.add = lambda obj: stored_histories.append(obj)
    mock_session.scalar = AsyncMock(return_value=None)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.use_account_attribution_setting = True
    mock_client.get_multi_period_insights = AsyncMock(return_value={
        ("2026-10-03", "2026-10-03"): {"spend": "46.45", "impressions": "52040", "reach": "48755", "clicks": "568"},
        ("2026-10-02", "2026-10-02"): {"spend": "46.66", "impressions": "56411", "reach": "52493", "clicks": "529"},
    })
    mock_client.get_campaign_insights = AsyncMock(side_effect=[
        # curr period campaign insights
        [{"campaign_id": "c1", "results": [{"indicator": "total_profile_visits", "values": [{"value": "391"}]}]}],
        # prev period campaign insights
        [{"campaign_id": "c1", "results": [{"indicator": "total_profile_visits", "values": [{"value": "315"}]}]}],
    ])

    # Emulate sent telegram message returning an object with message_id=8888
    sent_msg_mock = MagicMock()
    sent_msg_mock.message_id = 8888

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock, return_value=sent_msg_mock):

        res = await SchedulerService.execute_report("rep_snap_1", is_test=False, cache_bypass=True)
        assert res["status"] == "success"

        # Check campaign insights were called twice (for curr and prev periods)
        assert mock_client.get_campaign_insights.call_count == 2

        # Check RunHistory has telegram_message_id and raw_meta_snapshot
        assert len(stored_histories) >= 1
        final_history = stored_histories[0]
        assert final_history.telegram_message_id == 8888
        assert final_history.raw_meta_snapshot is not None
        assert "fetched_at" in final_history.raw_meta_snapshot
        assert final_history.raw_meta_snapshot["attribution_mode"] == "account"
        assert final_history.raw_meta_snapshot["campaign_insights"] is not None
        assert "prev_period" in final_history.raw_meta_snapshot

        # Check exact profile visits were used without approximate mark
        assert res["metrics"]["profile_visits"] == 391
        assert "profile_visits" not in res["metrics"]["approximate_metrics"]


@pytest.mark.asyncio
async def test_scheduler_skips_campaign_insights_when_profile_visits_not_selected():
    """
    Verifies that get_campaign_insights is NOT called if 'profile_visits' is omitted
    from selected metrics, saving API rate limits and network latency.
    """
    mock_report = MagicMock()
    mock_report.id = "rep_no_pv"
    mock_report.user_id = 1
    mock_report.name = "No Profile Visits"
    mock_report.periodicity = "daily"
    mock_report.account_timezone = "Asia/Tashkent"
    mock_report.schedule_time = "09:00"
    mock_report.send_timezone = "Asia/Tashkent"
    mock_report.schedule_weekday = 0
    mock_report.schedule_monthday = 1
    mock_report.campaign_scope_type = "all"
    mock_report.meta_account_id = "act_888"
    mock_report.currency = "USD"
    mock_report.metrics = ["spend", "impressions", "clicks"]
    mock_report.metric_labels = {}
    mock_report.metric_lang = "ru"
    mock_report.show_comparison = False
    mock_report.destinations = []

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "enc_token"
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
    mock_client.get_insights = AsyncMock(return_value={"spend": "30.00", "impressions": "5000", "clicks": "120"})
    mock_client.get_campaign_insights = AsyncMock()

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"):

        res = await SchedulerService.execute_report("rep_no_pv", is_test=False, cache_bypass=True)
        assert res["status"] == "success"
        # get_campaign_insights was never called
        mock_client.get_campaign_insights.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_duplicate_defense_sending_integrity_error():
    """
    Verifies that if two workers race to insert status='sending' for the same period,
    the second worker encountering an IntegrityError safely skips execution without crashing
    and without double-delivering Telegram messages.
    """
    from sqlalchemy.exc import IntegrityError

    mock_report = MagicMock()
    mock_report.id = "rep_race"
    mock_report.user_id = 1
    mock_report.name = "Race Report"
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

    mock_user = MagicMock()
    mock_meta_conn = MagicMock()
    mock_meta_conn.encrypted_access_token = "enc_token"
    mock_user.meta_connection = mock_meta_conn
    mock_report.user = mock_user

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.scalar = AsyncMock(return_value=None)
    mock_report_res = MagicMock()
    mock_report_res.scalars().first.return_value = mock_report
    mock_session.execute = AsyncMock(return_value=mock_report_res)

    # First commit in Phase 1 raises IntegrityError (simulating concurrent insert)
    mock_session.commit = AsyncMock(side_effect=IntegrityError("duplicate key", params=None, orig=None))
    mock_session.rollback = AsyncMock()

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    mock_client = MagicMock()
    mock_client.get_insights = AsyncMock(return_value={"spend": "50.00", "impressions": "1000"})

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls), \
         patch("app.services.scheduler_service.MetaClient", return_value=mock_client), \
         patch("app.services.scheduler_service.decrypt_secret", return_value="raw_token"), \
         patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_tg:

        res = await SchedulerService.execute_report("rep_race", is_test=False, cache_bypass=True)
        assert res["status"] == "skipped"
        assert "Duplicate run detected" in res["message"]
        mock_tg.assert_not_called()
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_old_raw_snapshots():
    """
    Verifies that cleanup_old_raw_snapshots executes update query setting
    raw_meta_snapshot=None for records older than the cutoff threshold (90 days).
    """
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.rowcount = 7
    mock_session.execute = AsyncMock(return_value=mock_res)
    mock_session.commit = AsyncMock()

    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = mock_session
    mock_session_cls.return_value.__aexit__.return_value = None

    with patch("app.services.scheduler_service.AsyncSessionLocal", mock_session_cls):
        count = await SchedulerService.cleanup_old_raw_snapshots(days=90)
        assert count == 7
        assert mock_session.execute.called
        assert mock_session.commit.called

        # Verify update statement was executed
        executed_stmt = mock_session.execute.call_args[0][0]
        sql_str = str(executed_stmt)
        assert "UPDATE run_histories" in sql_str
        assert "raw_meta_snapshot" in sql_str



