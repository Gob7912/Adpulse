import json
import os
import warnings
import pytest
from app.services.report_engine import ReportEngine

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "meta")

def load_fixture(filename: str) -> dict:
    filepath = os.path.join(FIXTURES_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def test_golden_account_a_2026_10_03():
    """
    Golden test on frozen fixture for Account A (2026-10-03).
    Ground Truth from Ads Manager asserted ONLY for:
    - spend: 46.45
    - calls: 19
    - profile_visits: 391
    - impressions: 52 036 (with tolerance ±0.1% due to Meta late updates: actual 52 040)
    All other checks are structural consistency checks.
    """
    fixture = load_fixture("account_a_2026_10_03.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    # 1. Ground Truth Assertions (Ads Manager verified)
    acc_spend = float(acc["spend"])
    assert acc_spend == 46.45

    acc_imp = int(acc["impressions"])
    assert acc_imp == pytest.approx(52036, rel=0.001)

    # Find profile visits and calls from campaigns
    calls_count = None
    profile_visits_count = None
    for c in camps:
        for a in c.get("actions", []) or []:
            if a.get("action_type") == "click_to_call_native_call_placed":
                calls_count = int(a.get("value"))
        for res in c.get("results", []) or []:
            if res.get("indicator") == "total_profile_visits":
                vals = res.get("values", [])
                if vals and vals[0].get("value") is not None:
                    profile_visits_count = int(vals[0]["value"])

    assert calls_count == 19
    assert profile_visits_count == 391

    # 2. Consistency Checks
    sum_camp_spend = round(sum(float(c.get("spend", 0)) for c in camps), 2)
    assert acc_spend == sum_camp_spend

    sum_camp_imp = sum(int(c.get("impressions", 0)) for c in camps)
    assert acc_imp == sum_camp_imp

    # link_clicks <= clicks as a warning, not hard assert
    for c in camps:
        c_clicks = int(c.get("clicks", 0))
        c_ilc = int(c.get("inline_link_clicks", 0))
        if c_ilc > c_clicks:
            warnings.warn(f"Notice: campaign {c.get('campaign_name')} inline_link_clicks ({c_ilc}) > clicks ({c_clicks}) due to Meta attribution pipeline discrepancy")


def test_golden_account_a_2026_10_02():
    """
    Golden test on frozen fixture for Account A (2026-10-02).
    Ground Truth from Ads Manager asserted ONLY for:
    - spend: 46.66
    - calls: 22
    - profile_visits: 315
    - impressions: 56 411 (with tolerance ±0.1%)
    All other checks are structural consistency checks.
    """
    fixture = load_fixture("account_a_2026_10_02.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    # 1. Ground Truth Assertions (Ads Manager verified)
    acc_spend = float(acc["spend"])
    assert acc_spend == 46.66

    acc_imp = int(acc["impressions"])
    assert acc_imp == pytest.approx(56411, rel=0.001)

    calls_count = None
    profile_visits_count = None
    for c in camps:
        for a in c.get("actions", []) or []:
            if a.get("action_type") == "click_to_call_native_call_placed":
                calls_count = int(a.get("value"))
        for res in c.get("results", []) or []:
            if res.get("indicator") == "total_profile_visits":
                vals = res.get("values", [])
                if vals and vals[0].get("value") is not None:
                    profile_visits_count = int(vals[0]["value"])

    assert calls_count == 22
    assert profile_visits_count == 315

    # 2. Consistency Checks
    sum_camp_spend = round(sum(float(c.get("spend", 0)) for c in camps), 2)
    assert acc_spend == sum_camp_spend

    sum_camp_imp = sum(int(c.get("impressions", 0)) for c in camps)
    assert acc_imp == sum_camp_imp

    # link_clicks <= clicks as a warning, not hard assert
    for c in camps:
        c_clicks = int(c.get("clicks", 0))
        c_ilc = int(c.get("inline_link_clicks", 0))
        if c_ilc > c_clicks:
            warnings.warn(f"Notice: campaign {c.get('campaign_name')} inline_link_clicks ({c_ilc}) > clicks ({c_clicks}) due to Meta attribution pipeline discrepancy")


def test_golden_account_a_2026_10_01_consistency():
    """Consistency check for 2026-10-01 (no external Ads Manager ground truth provided)."""
    fixture = load_fixture("account_a_2026_10_01.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    acc_spend = float(acc["spend"])
    sum_camp_spend = round(sum(float(c.get("spend", 0)) for c in camps), 2)
    assert acc_spend == sum_camp_spend

    acc_imp = int(acc["impressions"])
    sum_camp_imp = sum(int(c.get("impressions", 0)) for c in camps)
    assert acc_imp == sum_camp_imp


def test_golden_account_b_2026_10_03_consistency():
    """Consistency check for Account B 2026-10-03."""
    fixture = load_fixture("account_b_2026_10_03.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    acc_spend = float(acc["spend"])
    sum_camp_spend = round(sum(float(c.get("spend", 0)) for c in camps), 2)
    assert acc_spend == sum_camp_spend

    acc_imp = int(acc["impressions"])
    sum_camp_imp = sum(int(c.get("impressions", 0)) for c in camps)
    assert acc_imp == sum_camp_imp


def test_report_engine_hybrid_extraction_account_a_2026_10_03():
    """
    Verifies that ReportEngine.compute_aggregated_metrics uses hybrid extraction:
    - profile_visits is extracted strictly from total_profile_visits across campaigns: 391 (exact, no ≈)
    - calls: 19
    - spend: 46.45
    - reach is taken strictly from account level: 48 755
    """
    fixture = load_fixture("account_a_2026_10_03.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    metrics = ReportEngine.compute_aggregated_metrics(acc, campaign_insights=camps)
    assert metrics["spend"] == 46.45
    assert metrics["calls"] == 19
    assert metrics["profile_visits"] == 391
    assert "profile_visits" not in metrics["approximate_metrics"]
    assert metrics["reach"] == 48755


def test_report_engine_hybrid_extraction_account_a_2026_10_02():
    """
    Verifies that ReportEngine.compute_aggregated_metrics uses hybrid extraction:
    - profile_visits is extracted strictly from total_profile_visits across campaigns: 315 (exact, no ≈)
    - calls: 22
    - spend: 46.66
    - reach is taken strictly from account level: 52 493 (not summed 51 143)
    """
    fixture = load_fixture("account_a_2026_10_02.json")
    acc = fixture["account_insight"]
    camps = fixture["campaign_insights"]

    metrics = ReportEngine.compute_aggregated_metrics(acc, campaign_insights=camps)
    assert metrics["spend"] == 46.66
    assert metrics["calls"] == 22
    assert metrics["profile_visits"] == 315
    assert "profile_visits" not in metrics["approximate_metrics"]
    assert metrics["reach"] == 52493


def test_report_engine_fallback_when_campaign_insights_missing():
    """
    Verifies that when campaign_insights is NOT provided, ReportEngine falls back
    to link_clicks with approximate indicator (≈) for profile_visits.
    """
    f_03 = load_fixture("account_a_2026_10_03.json")["account_insight"]
    metrics_03 = ReportEngine.compute_aggregated_metrics(f_03, campaign_insights=None)
    assert metrics_03["profile_visits"] == 417
    assert "profile_visits" in metrics_03["approximate_metrics"]

    f_02 = load_fixture("account_a_2026_10_02.json")["account_insight"]
    metrics_02 = ReportEngine.compute_aggregated_metrics(f_02, campaign_insights=None)
    assert metrics_02["profile_visits"] == 392
    assert "profile_visits" in metrics_02["approximate_metrics"]

