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


def test_calculate_period_dates_test_live():
    ref_dt = datetime(2026, 10, 4, 14, 23, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
    since_d, until_d, period_end_dt = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Asia/Tashkent",
        reference_dt=ref_dt,
        is_test=True
    )
    # Live manual trigger must strictly return current calendar day in Asia/Tashkent
    assert since_d == "2026-10-04"
    assert until_d == "2026-10-04"
    assert period_end_dt.day == 4


def test_telegram_live_report_header():
    vals = {"spend": 14.57, "impressions": 5000}
    
    # RU test run
    msg_ru = ReportEngine.build_telegram_message(
        report_name="Клиент Beta",
        account_name="Beta Account",
        currency="USD",
        periodicity="daily",
        since_date="2026-10-04",
        until_date="2026-10-04",
        selected_metrics=["spend", "impressions"],
        metric_values=vals,
        lang="ru",
        is_test=True,
        account_timezone="Asia/Tashkent",
        as_of_time="14:23"
    )
    assert "LIVE" in msg_ru
    assert "2026-10-04" in msg_ru
    assert "(USD • Asia/Tashkent)" in msg_ru
    assert "данные на 14:23, неполные" in msg_ru

    # UZ test run
    msg_uz = ReportEngine.build_telegram_message(
        report_name="Beta Mijoz",
        account_name="Beta Account",
        currency="USD",
        periodicity="daily",
        since_date="2026-10-04",
        until_date="2026-10-04",
        selected_metrics=["spend", "impressions"],
        metric_values=vals,
        lang="uz",
        is_test=True,
        account_timezone="Asia/Tashkent",
        as_of_time="14:23"
    )
    assert "(USD • Asia/Tashkent)" in msg_uz
    assert "soat 14:23 holatiga ko'ra, to'liq emas" in msg_uz

    # EN test run
    msg_en = ReportEngine.build_telegram_message(
        report_name="Beta Client",
        account_name="Beta Account",
        currency="EUR",
        periodicity="daily",
        since_date="2026-10-04",
        until_date="2026-10-04",
        selected_metrics=["spend", "impressions"],
        metric_values=vals,
        lang="en",
        is_test=True,
        account_timezone="Europe/Berlin",
        as_of_time="11:23"
    )
    assert "(EUR • Europe/Berlin)" in msg_en
    assert "data as of 11:23, incomplete" in msg_en


def test_calculate_period_dates_timezone_boundaries():
    # Instant in UTC: 2026-10-04 02:30:00 UTC
    utc_moment = datetime(2026, 10, 4, 2, 30, 0, tzinfo=timezone.utc)

    # 1. UTC-4: America/New_York (EDT, UTC-4). In NY, this is 2026-10-03 22:30:00 (still Oct 3!)
    ny_since, ny_until, ny_end = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="America/New_York",
        reference_dt=utc_moment,
        is_test=False
    )
    # Yesterday relative to Oct 3 in NY is Oct 2
    assert ny_since == "2026-10-02"
    assert ny_until == "2026-10-02"

    ny_test_since, ny_test_until, _ = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="America/New_York",
        reference_dt=utc_moment,
        is_test=True
    )
    # Today in NY is Oct 3
    assert ny_test_since == "2026-10-03"
    assert ny_test_until == "2026-10-03"

    # 2. UTC+5: Asia/Tashkent. In Tashkent, this is 2026-10-04 07:30:00 (already Oct 4!)
    tsh_since, tsh_until, _ = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Asia/Tashkent",
        reference_dt=utc_moment,
        is_test=False
    )
    assert tsh_since == "2026-10-03"
    assert tsh_until == "2026-10-03"

    tsh_test_since, tsh_test_until, _ = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Asia/Tashkent",
        reference_dt=utc_moment,
        is_test=True
    )
    assert tsh_test_since == "2026-10-04"
    assert tsh_test_until == "2026-10-04"

    # 3. UTC+2: Etc/GMT-2 (or Africa/Cairo). In UTC+2, this is 2026-10-04 04:30:00 (Oct 4!)
    cairo_since, cairo_until, _ = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Etc/GMT-2",
        reference_dt=utc_moment,
        is_test=False
    )
    assert cairo_since == "2026-10-03"
    assert cairo_until == "2026-10-03"

    cairo_test_since, cairo_test_until, _ = ReportEngine.calculate_period_dates(
        periodicity="daily",
        account_tz_str="Etc/GMT-2",
        reference_dt=utc_moment,
        is_test=True
    )
    assert cairo_test_since == "2026-10-04"
    assert cairo_test_until == "2026-10-04"


def test_final_data_delay_utc_minus_4():
    # NY ad account: period ends 2026-10-03 23:59:59 EDT (which is 2026-10-04 03:59:59 UTC)
    tz_ny = ZoneInfo("America/New_York")
    ny_end_dt = datetime(2026, 10, 3, 23, 59, 59, tzinfo=tz_ny)

    is_ready, ready_at_utc = ReportEngine.check_final_data_delay(ny_end_dt, "America/New_York", delay_hours=6)
    expected_ready_utc = datetime(2026, 10, 4, 9, 59, 59, tzinfo=timezone.utc)
    assert ready_at_utc == expected_ready_utc


def test_calculate_comparison_dates():
    ref_dt = datetime(2026, 10, 4, 14, 0, 0, tzinfo=ZoneInfo("Asia/Tashkent"))

    # 1. Daily: yesterday (Oct 3) vs day before yesterday (Oct 2)
    c_s, c_u, p_s, p_u, _ = ReportEngine.calculate_comparison_dates("daily", "Asia/Tashkent", ref_dt, is_test=False)
    assert c_s == "2026-10-03"
    assert c_u == "2026-10-03"
    assert p_s == "2026-10-02"
    assert p_u == "2026-10-02"

    # 2. Test run: today, NO previous period
    tc_s, tc_u, tp_s, tp_u, _ = ReportEngine.calculate_comparison_dates("daily", "Asia/Tashkent", ref_dt, is_test=True)
    assert tc_s == "2026-10-04"
    assert tc_u == "2026-10-04"
    assert tp_s is None
    assert tp_u is None

    # 3. Weekly: last week vs week before last
    # Oct 4, 2026 is Sunday. Last week was Mon Sep 21 to Sun Sep 27 (since Sunday Oct 4 is still current week in Python weekday 6)
    wc_s, wc_u, wp_s, wp_u, _ = ReportEngine.calculate_comparison_dates("weekly", "Asia/Tashkent", ref_dt, is_test=False)
    assert wc_s == "2026-09-21"
    assert wc_u == "2026-09-27"
    assert wp_s == "2026-09-14"
    assert wp_u == "2026-09-20"

    # 4. Monthly: Sep 2026 (30 days) vs Aug 2026 (31 days)
    mc_s, mc_u, mp_s, mp_u, _ = ReportEngine.calculate_comparison_dates("monthly", "Asia/Tashkent", ref_dt, is_test=False)
    assert mc_s == "2026-09-01"
    assert mc_u == "2026-09-30"
    assert mp_s == "2026-08-01"
    assert mp_u == "2026-08-31"


def test_calculate_metrics_deltas_math_and_polarity():
    curr = {
        "spend": 110.0,
        "impressions": 10000,
        "reach": 8000,
        "clicks": 500,
        "cpc": 0.22,
        "cpl": 4.50,
        "leads": 20,
        "messages": 15,
        "roas": 3.5,
        "calls": 10,
        "approximate_metrics": []
    }
    prev = {
        "spend": 100.0,
        "impressions": 12000,
        "reach": 8000,
        "clicks": 500,
        "cpc": 0.20,
        "cpl": 5.00,
        "leads": 10,
        "messages": 20,
        "roas": 0.0,  # Zero in previous period -> should be "new"
        "calls": 10,
        "approximate_metrics": []
    }

    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)

    # 1. Neutral metrics: spend, impressions, reach, clicks (no green/red emojis)
    assert deltas["spend"]["badge"] == "▲ +10%"
    assert deltas["impressions"]["badge"] == "▼ -17%"
    assert deltas["reach"]["badge"] == "= 0%"
    assert deltas["clicks"]["badge"] == "= 0%"

    # 2. Lower is better: cpc (+10% cost increase -> bad), cpl (-10% cost decrease -> good)
    assert deltas["cpc"]["badge"] == "🔴 ▲ +10%"
    assert deltas["cpl"]["badge"] == "🟢 ▼ -10%"

    # 3. Higher is better: leads (+100% -> good), messages (-25% -> bad)
    assert deltas["leads"]["badge"] == "🟢 ▲ +100%"
    assert deltas["messages"]["badge"] == "🔴 ▼ -25%"

    # 4. Zero in previous period (ROAS was 0, now 3.5) -> "🆕 new"
    assert deltas["roas"]["badge"] == "🆕 new"
    assert deltas["roas"]["diff_pct"] is None


def test_mixed_fallback_delta_suppression():
    # Case A: profile_visits is fallback in curr, direct in prev -> delta suppressed
    curr_mixed = {
        "profile_visits": 114,
        "calls": 4,
        "approximate_metrics": ["profile_visits"]
    }
    prev_mixed = {
        "profile_visits": 100,
        "calls": 3,
        "approximate_metrics": []
    }
    deltas = ReportEngine.calculate_metrics_deltas(curr_mixed, prev_mixed)
    assert deltas["profile_visits"]["diff_pct"] is None
    assert deltas["profile_visits"]["badge"] is None
    assert deltas["profile_visits"]["status"] == "mixed_fallback"
    # calls: direct in both -> delta computed!
    assert deltas["calls"]["badge"] == "🟢 ▲ +33%"

    # Case B: both are approximate -> delta suppressed (prompt 9 / BUGS_AUDIT item 1.3)
    curr_both_approx = {
        "profile_visits": 150,
        "approximate_metrics": ["profile_visits"]
    }
    prev_both_approx = {
        "profile_visits": 100,
        "approximate_metrics": ["profile_visits"]
    }
    deltas_both = ReportEngine.calculate_metrics_deltas(curr_both_approx, prev_both_approx)
    assert deltas_both["profile_visits"]["badge"] is None
    assert deltas_both["profile_visits"]["diff_pct"] is None
    assert deltas_both["profile_visits"]["status"] == "approximate_suppressed"


def test_telegram_message_with_deltas_and_monthly_note():
    curr = {
        "spend": 14.57,
        "leads": 4,
        "cpl": 3.64,
        "profile_visits": 114,
        "approximate_metrics": ["profile_visits"]
    }
    prev = {
        "spend": 46.45,
        "leads": 2,
        "cpl": 23.22,
        "profile_visits": 100,
        "approximate_metrics": ["profile_visits"]
    }
    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)

    # 1. Clean primary message (Message 1)
    msg = ReportEngine.build_telegram_message(
        report_name="MC - All Generators",
        account_name="Account A",
        currency="USD",
        periodicity="monthly",
        since_date="2026-09-01",
        until_date="2026-09-30",
        selected_metrics=["spend", "leads", "cpl", "profile_visits"],
        metric_values=curr,
        lang="ru",
        account_timezone="Asia/Tashkent"
    )

    assert "• <b>Расход</b>: <code>$14.57</code>" in msg
    assert "• <b>Лиды</b>: <code>4</code>" in msg
    assert "• <b>CPL (цена за лид)</b>: <code>$3.64</code>" in msg
    assert "• <b>Посещения профиля</b>: <code>≈ 114</code>" in msg
    assert "▼" not in msg
    assert "▲" not in msg
    assert "🟢" not in msg
    assert "🔴" not in msg

    # 2. Comparison message (Message 2)
    comp_msg = ReportEngine.build_comparison_message(
        report_name="MC - All Generators",
        account_name="Account A",
        currency="USD",
        periodicity="monthly",
        curr_since="2026-09-01",
        curr_until="2026-09-30",
        prev_since="2026-08-01",
        prev_until="2026-08-31",
        selected_metrics=["spend", "leads", "cpl", "profile_visits"],
        curr_metric_values=curr,
        prev_metric_values=prev,
        deltas=deltas,
        lang="ru",
        account_timezone="Asia/Tashkent"
    )

    # Monthly note
    assert "(31 дн. → 30 дн.)" in comp_msg
    # Grouped blocks
    assert "Общие показатели" in comp_msg
    assert "Конверсии и стоимость" in comp_msg
    # "was → became" format
    assert "• <b>Расход</b>: <code>$46.45</code> → <code>$14.57</code> ▼ -69%" in comp_msg
    assert "• <b>Лиды</b>: <code>2</code> → <code>4</code> 🟢 ▲ +100%" in comp_msg
    assert "• <b>CPL (цена за лид)</b>: <code>$23.22</code> → <code>$3.64</code> 🟢 ▼ -84%" in comp_msg
    # Approximate profile visits: has ≈ and suppressed delta badge
    assert "• <b>Посещения профиля</b>: <code>≈ 100</code> → <code>≈ 114</code>" in comp_msg
    assert "114</code> (" not in comp_msg  # no delta badge in parenthesis
    assert "114</code> 🟢" not in comp_msg


def test_sheets_data_with_numeric_deltas():
    curr = {"spend": 100.0, "leads": 10}
    prev = {"spend": 80.0, "leads": 5}
    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)

    headers, row = ReportEngine.build_sheets_row_data(
        report_name="Test Report",
        since_date="2026-10-03",
        until_date="2026-10-03",
        selected_metrics=["spend", "leads"],
        metric_values=curr,
        lang="ru",
        deltas=deltas
    )

    assert "Δ Расход (%)" in headers
    assert "Δ Лиды (%)" in headers
    spend_idx = headers.index("Расход")
    delta_spend_idx = headers.index("Δ Расход (%)")
    leads_idx = headers.index("Лиды")
    delta_leads_idx = headers.index("Δ Лиды (%)")

    assert row[spend_idx] == 100.0
    assert row[leads_idx] == 10
    # Values must be numeric floats, not string emojis
    assert isinstance(row[delta_spend_idx], float)
    assert row[delta_spend_idx] == 25.0
    assert isinstance(row[delta_leads_idx], float)
    assert row[delta_leads_idx] == 100.0


def test_sub_one_percent_deltas_and_exact_zero():
    """
    Verifies:
    1. |Δ| < 1% shows 1 decimal place (-0.5%, +0.3%).
    2. '= 0%' appears ONLY when values are strictly identical.
    """
    # 1. Exact zero
    curr_eq = {"spend": 100.0, "reach": 5000}
    prev_eq = {"spend": 100.0, "reach": 5000}
    d_eq = ReportEngine.calculate_metrics_deltas(curr_eq, prev_eq)
    assert d_eq["spend"]["badge"] == "= 0%"
    assert d_eq["spend"]["diff_pct"] == 0.0
    assert d_eq["reach"]["badge"] == "= 0%"

    # 2. Spend (neutral): +0.3%
    curr_sp_pos = {"spend": 100.3}
    prev_sp = {"spend": 100.0}
    d_sp_pos = ReportEngine.calculate_metrics_deltas(curr_sp_pos, prev_sp)
    assert d_sp_pos["spend"]["badge"] == "▲ +0.3%"
    assert d_sp_pos["spend"]["diff_pct"] == 0.3

    # 3. Spend (neutral): -0.5%
    curr_sp_neg = {"spend": 99.5}
    d_sp_neg = ReportEngine.calculate_metrics_deltas(curr_sp_neg, prev_sp)
    assert d_sp_neg["spend"]["badge"] == "▼ -0.5%"
    assert d_sp_neg["spend"]["diff_pct"] == -0.5

    # 4. CPC (lower is better): +0.5% -> bad (🔴), -0.5% -> good (🟢)
    curr_cpc_up = {"cpc": 0.201, "spend": 201.0, "clicks": 1000}
    prev_cpc = {"cpc": 0.200, "spend": 200.0, "clicks": 1000}
    d_cpc_up = ReportEngine.calculate_metrics_deltas(curr_cpc_up, prev_cpc)
    assert d_cpc_up["cpc"]["badge"] == "🔴 ▲ +0.5%"

    curr_cpc_down = {"cpc": 0.199, "spend": 199.0, "clicks": 1000}
    d_cpc_down = ReportEngine.calculate_metrics_deltas(curr_cpc_down, prev_cpc)
    assert d_cpc_down["cpc"]["badge"] == "🟢 ▼ -0.5%"

    # 5. Leads (higher is better): +0.3% -> good (🟢), -0.5% -> bad (🔴)
    curr_ld_up = {"leads": 1003}
    prev_ld = {"leads": 1000}
    d_ld_up = ReportEngine.calculate_metrics_deltas(curr_ld_up, prev_ld)
    assert d_ld_up["leads"]["badge"] == "🟢 ▲ +0.3%"

    curr_ld_down = {"leads": 995}
    d_ld_down = ReportEngine.calculate_metrics_deltas(curr_ld_down, prev_ld)
    assert d_ld_down["leads"]["badge"] == "🔴 ▼ -0.5%"


def test_half_away_from_zero_percentage_rounding():
    """
    Verifies that .5 is rounded away from zero:
    -12.5% -> -13%
    +12.5% -> +13%
    """
    # +12.5%: spend 112.5 vs 100.0
    curr_pos = {"spend": 112.5}
    prev = {"spend": 100.0}
    d_pos = ReportEngine.calculate_metrics_deltas(curr_pos, prev)
    assert d_pos["spend"]["badge"] == "▲ +13%"

    # -12.5%: spend 87.5 vs 100.0
    curr_neg = {"spend": 87.5}
    d_neg = ReportEngine.calculate_metrics_deltas(curr_neg, prev)
    assert d_neg["spend"]["badge"] == "▼ -13%"


def test_comparison_message_omits_double_nd_and_keeps_val_to_nd():
    """
    Verifies that build_comparison_message:
    1. OMITs rows where both values are None (never renders 'н/д → н/д').
    2. KEEPs rows of form 'значение → н/д' without a percentage badge.
    """
    curr = {
        "spend": 100.0,
        "calls": 10,
        "new_followers": None,
        "leads": None,
        "cpl": None,
        "roas": None,
    }
    prev = {
        "spend": 100.0,
        "calls": 8,
        "new_followers": 2,
        "leads": None,
        "cpl": None,
        "roas": None,
    }
    deltas = ReportEngine.calculate_metrics_deltas(curr, prev)
    selected = ["spend", "calls", "new_followers", "leads", "cpl", "roas"]

    msg = ReportEngine.build_comparison_message(
        report_name="Omit ND Test",
        account_name="Acc",
        currency="USD",
        periodicity="daily",
        curr_since="2026-10-03",
        curr_until="2026-10-03",
        prev_since="2026-10-02",
        prev_until="2026-10-02",
        selected_metrics=selected,
        curr_metric_values=curr,
        prev_metric_values=prev,
        deltas=deltas,
        lang="ru"
    )

    # 1. 'н/д → н/д' should NOT be present anywhere in the message
    assert "н/д → н/д" not in msg
    assert "Лиды" not in msg
    assert "CPL" not in msg
    assert "ROAS" not in msg

    # 2. 'значение → н/д' (new_followers) MUST be kept without any percentage badge
    assert "• <b>Новые подписчики</b>: <code>2</code> → <code>н/д</code>" in msg
    assert "н/д</code> (" not in msg
    assert "н/д</code> %" not in msg

    # 3. Present metrics render normally
    assert "• <b>Расход</b>: <code>$100.00</code> → <code>$100.00</code> = 0%" in msg
    assert "• <b>Звонки</b>: <code>8</code> → <code>10</code> 🟢 ▲ +25%" in msg


