import pytest
from app.services.report_engine import ReportEngine
from app.services.meta_metrics import format_metric_value, get_default_labels
from app.config import settings

def test_meta_graph_api_version_config():
    assert settings.META_GRAPH_API_VERSION == "v21.0"
    assert settings.META_GRAPH_API_BASE == "https://graph.facebook.com/v21.0"

def test_metrics_aggregation_and_strict_ratios():
    raw_insight = {
        "spend": "150.00",
        "impressions": "30000",
        "clicks": "1200",
        "inline_link_clicks": "600",
        "reach": "25000",
        "actions": [
            {"action_type": "lead", "value": "20"},
            {"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "20"},
            {"action_type": "phone_call", "value": "6"},
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
    assert metrics["ctr"] == 4.0
    assert metrics["ctr_link"] == 2.0
    assert metrics["cpc"] == 0.12
    assert metrics["cpm"] == 5.0
    assert metrics["cpp"] == 6.0

    # Conversions & Actions
    assert metrics["leads"] == 20
    assert metrics["cpl"] == 7.50

    assert metrics["messages"] == 20
    assert metrics["cost_per_dm"] == 7.50

    assert metrics["calls"] == 6
    assert metrics["cost_per_call"] == 25.0

    assert metrics["app_installs"] == 10
    assert metrics["cost_per_install"] == 15.0

    assert metrics["video_views"] == 1500
    assert metrics["post_engagement"] == 850
    assert metrics["landing_page_views"] == 520

    # ROAS = 450 / 150 = 3.0
    assert metrics["roas"] == 3.0

def test_lead_form_campaign_without_messaging_and_no_followers():
    """
    Simulates real Ads Manager case:
    A Leads (Form) campaign with $26 spend, 51 leads, 26k reach, and 9236 post engagements.
    Verifies that:
    1. 'new_followers' is None (not 9,236 from post/page engagement)
    2. 'messages' and 'cost_per_dm' are None (not 119 and $0.22)
    3. 'leads' is 51 and CPL is $0.51 ($26 / 51)
    """
    lead_campaign_insight = {
        "spend": "26.00",
        "impressions": "31000",
        "clicks": "450",
        "inline_link_clicks": "220",
        "reach": "26000",
        "actions": [
            {"action_type": "lead", "value": "51"},
            {"action_type": "onsite_conversion.lead_grouped", "value": "51"},
            {"action_type": "post_engagement", "value": "9236"},
            {"action_type": "page_engagement", "value": "9236"},
            {"action_type": "onsite_conversion.total_messaging_connection", "value": "119"}
        ]
    }

    metrics = ReportEngine.compute_aggregated_metrics(lead_campaign_insight)

    # Leads must not be double counted
    assert metrics["leads"] == 51
    assert metrics["cpl"] == 0.51

    # New followers must be None (never 9,236)
    assert metrics["new_followers"] is None

    # Messages must not use total_messaging_connection
    assert metrics["messages"] is None
    assert metrics["cost_per_dm"] is None

def test_zero_division_safety_and_none_handling():
    empty_insight = {}
    metrics = ReportEngine.compute_aggregated_metrics(empty_insight)
    assert metrics["spend"] == 0.0
    assert metrics["impressions"] == 0
    assert metrics["clicks"] == 0
    assert metrics["ctr"] == 0.0
    # Undefined ratios must be None (never a fake 0.00)
    assert metrics["cpc"] is None
    assert metrics["cpm"] is None
    assert metrics["cpp"] is None
    assert metrics["cpl"] is None
    assert metrics["cost_per_dm"] is None
    assert metrics["roas"] is None
    # Formatting None must produce localized N/A
    assert format_metric_value(metrics["cpc"], "currency", "USD", lang="ru") == "н/д"
    assert format_metric_value(metrics["cost_per_dm"], "currency", "USD", lang="en") == "N/A"

def test_metric_value_formatting():
    assert format_metric_value(145.2, "currency", "USD", lang="ru") == "$145.20"
    assert format_metric_value(1500000.0, "currency", "UZS", lang="uz") == "1,500,000.00 UZS"
    assert format_metric_value(3.845, "percent", lang="ru") == "3.85%"
    assert format_metric_value(28450, "integer", lang="ru") == "28 450"
    assert format_metric_value(4.256, "decimal", lang="ru") == "4.26"
    
    # None values must show localized N/A, never a fake 0
    assert format_metric_value(None, "currency", "USD", lang="ru") == "н/д"
    assert format_metric_value(None, "integer", "USD", lang="en") == "N/A"
    assert format_metric_value(None, "decimal", "USD", lang="uz") == "mavjud emas"

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
