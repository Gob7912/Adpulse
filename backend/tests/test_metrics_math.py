import pytest
from app.services.report_engine import ReportEngine
from app.services.meta_metrics import format_metric_value, get_default_labels

def test_metrics_aggregation_and_strict_ratios():
    raw_insight = {
        "spend": "150.00",
        "impressions": "30000",
        "clicks": "1200",
        "inline_link_clicks": "600",
        "reach": "25000",
        "actions": [
            {"action_type": "lead", "value": "15"},
            {"action_type": "onsite_conversion.lead_grouped", "value": "5"},
            {"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "20"},
            {"action_type": "call_confirm", "value": "6"},
            {"action_type": "mobile_app_install", "value": "10"},
            {"action_type": "video_thruplay_watched_actions", "value": "1500"},
            {"action_type": "post_engagement", "value": "850"},
            {"action_type": "landing_page_view", "value": "520"}
        ],
        "action_values": [
            {"action_type": "purchase", "value": "450.00"}
        ]
    }

    metrics = ReportEngine.compute_aggregated_metrics(raw_insight)

    # Core
    assert metrics["spend"] == 150.00
    assert metrics["impressions"] == 30000
    assert metrics["clicks"] == 1200
    assert metrics["link_clicks"] == 600
    assert metrics["reach"] == 25000

    # Ratios strictly computed from totals (never averaged)
    # CTR = 1200 / 30000 * 100 = 4.0%
    assert metrics["ctr"] == 4.0
    # CTR (link) = 600 / 30000 * 100 = 2.0%
    assert metrics["ctr_link"] == 2.0
    # CPC = 150 / 1200 = 0.125 -> 0.12 or 0.13 rounded
    assert metrics["cpc"] == 0.12
    # CPM = (150 / 30000) * 1000 = 5.0
    assert metrics["cpm"] == 5.0
    # CPP = (150 / 25000) * 1000 = 6.0
    assert metrics["cpp"] == 6.0

    # Conversions & Actions
    assert metrics["leads"] == 20  # 15 + 5
    assert metrics["cpl"] == 7.50  # 150 / 20

    assert metrics["messages"] == 20
    assert metrics["cost_per_dm"] == 7.50  # 150 / 20

    assert metrics["calls"] == 6
    assert metrics["cost_per_call"] == 25.0  # 150 / 6

    assert metrics["app_installs"] == 10
    assert metrics["cost_per_install"] == 15.0  # 150 / 10

    assert metrics["video_views"] == 1500
    assert metrics["post_engagement"] == 850
    assert metrics["landing_page_views"] == 520

    # ROAS = 450 / 150 = 3.0
    assert metrics["roas"] == 3.0

def test_zero_division_safety():
    empty_insight = {}
    metrics = ReportEngine.compute_aggregated_metrics(empty_insight)
    assert metrics["spend"] == 0.0
    assert metrics["impressions"] == 0
    assert metrics["clicks"] == 0
    assert metrics["ctr"] == 0.0
    assert metrics["cpc"] == 0.0
    assert metrics["cpm"] == 0.0
    assert metrics["cpp"] == 0.0
    assert metrics["cpl"] == 0.0
    assert metrics["cost_per_dm"] == 0.0
    assert metrics["roas"] == 0.0

def test_metric_value_formatting():
    assert format_metric_value(145.2, "currency", "USD") == "$145.20"
    assert format_metric_value(1500000.0, "currency", "UZS") == "1,500,000.00 UZS"
    assert format_metric_value(3.845, "percent") == "3.85%"
    assert format_metric_value(28450, "integer") == "28 450"
    assert format_metric_value(4.256, "decimal") == "4.26"
    assert format_metric_value(None, "currency") == "0"

def test_default_labels_translations():
    ru = get_default_labels("ru")
    uz = get_default_labels("uz")
    en = get_default_labels("en")

    assert ru["spend"] == "Расход"
    assert uz["spend"] == "Sarflangan mablag'"
    assert en["spend"] == "Spend"
    assert ru["leads"] == "Лиды"
    assert uz["leads"] == "Lidlar"
    assert en["leads"] == "Leads"
