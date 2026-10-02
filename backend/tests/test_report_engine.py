from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.report_engine import ReportEngine


def test_calculate_period_dates_daily():
    ref_dt = datetime(2026, 9, 29, 10, 0, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
    since_d, until_d, period_end_dt = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Asia/Tashkent",
        reference_dt=ref_dt
    )
    # Yesterday relative to Sep 29 is Sep 28
    assert since_d == "2026-09-28"
    assert until_d == "2026-09-28"
    assert period_end_dt.day == 28
    assert period_end_dt.hour == 23
    assert period_end_dt.minute == 59

def test_calculate_period_dates_weekly():
    # Tuesday Sep 29, 2026
    ref_dt = datetime(2026, 9, 29, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    since_d, until_d, period_end_dt = ReportEngine.calculate_period_dates(
        periodicity="weekly",
        account_tz_str="UTC",
        reference_dt=ref_dt
    )
    # Last full week was Monday Sep 21 to Sunday Sep 27
    assert since_d == "2026-09-21"
    assert until_d == "2026-09-27"
    assert period_end_dt.day == 27

def test_calculate_period_dates_monthly():
    ref_dt = datetime(2026, 9, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    since_d, until_d, period_end_dt = ReportEngine.calculate_period_dates(
        periodicity="monthly",
        account_tz_str="UTC",
        reference_dt=ref_dt
    )
    # Previous full month is August 2026 (Aug 1 to Aug 31)
    assert since_d == "2026-08-01"
    assert until_d == "2026-08-31"

def test_final_data_delay_check():
    tz = ZoneInfo("Asia/Tashkent")
    # Period ended at 23:59:59 on Sep 28
    period_end_dt = datetime(2026, 9, 28, 23, 59, 59, tzinfo=tz)

    # 1. 2 hours after period end (02:00 Sep 29) -> NOT ready (needs 6h)
    early_dt = period_end_dt + timedelta(hours=2)
    # Mocking now_utc logic
    is_ready, ready_at_utc = ReportEngine.check_final_data_delay(period_end_dt, "Asia/Tashkent", delay_hours=6)
    expected_ready_utc = (period_end_dt + timedelta(hours=6)).astimezone(timezone.utc)
    assert ready_at_utc == expected_ready_utc

def test_telegram_message_builder():
    sample_metrics = {
        "spend": 124.50,
        "impressions": 15000,
        "clicks": 450,
        "ctr": 3.0,
        "cpc": 0.28
    }
    msg = ReportEngine.build_telegram_message(
        report_name="Клиент Alpha",
        account_name="Alpha Store",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "impressions", "clicks", "ctr", "cpc"],
        metric_values=sample_metrics,
        lang="ru"
    )

    assert "Ежедневный отчёт: Клиент Alpha" in msg
    assert "Alpha Store" in msg
    assert "2026-09-28" in msg
    assert "$124.50" in msg
    assert "3.00%" in msg
    assert "Sent via" not in msg  # Ensure no third-party branding!

def test_telegram_zero_spend_fallback():
    zero_metrics = {
        "spend": 0.0,
        "impressions": 0,
        "clicks": 0
    }
    # RU
    msg_ru = ReportEngine.build_telegram_message(
        report_name="Тестовый отчёт",
        account_name="Тест Аккаунт",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "impressions"],
        metric_values=zero_metrics,
        lang="ru"
    )
    assert "За указанный период расходов и показов" in msg_ru

    # UZ
    msg_uz = ReportEngine.build_telegram_message(
        report_name="Test hisobot",
        account_name="Test Account",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "impressions"],
        metric_values=zero_metrics,
        lang="uz"
    )
    assert "xarajat va taassurotlar qayd etilmadi" in msg_uz

    # EN
    msg_en = ReportEngine.build_telegram_message(
        report_name="Test Report",
        account_name="Test Account",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "impressions"],
        metric_values=zero_metrics,
        lang="en"
    )
    assert "No spend or impressions recorded" in msg_en

def test_telegram_header_emojis():
    vals = {"spend": 50.0, "impressions": 1000, "leads": 5, "messages": 10}
    # Leads template emoji
    msg_leads = ReportEngine.build_telegram_message(
        report_name="Leads",
        account_name="Acc",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "leads"],
        metric_values=vals,
        template_type="lead_generation"
    )
    assert "🎯" in msg_leads

    # Direct messages emoji
    msg_dm = ReportEngine.build_telegram_message(
        report_name="DM",
        account_name="Acc",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "messages"],
        metric_values=vals,
        template_type="direct_messages"
    )
    assert "💬" in msg_dm

    # Pulse emoji
    msg_pulse = ReportEngine.build_telegram_message(
        report_name="Pulse",
        account_name="Acc",
        currency="USD",
        periodicity="daily",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "impressions"],
        metric_values=vals,
        template_type="daily_pulse"
    )
    assert "📊" in msg_pulse


def test_sheets_row_data_builder():
    sample_metrics = {"spend": 100.0, "leads": 25}
    headers, row = ReportEngine.build_sheets_row_data(
        report_name="Client X",
        since_date="2026-09-28",
        until_date="2026-09-28",
        selected_metrics=["spend", "leads"],
        metric_values=sample_metrics,
        lang="en"
    )
    assert headers[:3] == ["Дата генерации", "Период", "Название отчёта"]
    assert "Spend" in headers
    assert "Leads" in headers
    assert row[2] == "Client X"
    assert 100.0 in row
    assert 25 in row
