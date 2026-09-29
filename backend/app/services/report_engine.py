from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Optional
import logging

from app.config import settings
from app.services.meta_metrics import (
    METRIC_DEFINITIONS,
    MetricDefinition,
    format_metric_value,
    get_default_labels
)
from app.services.meta_client import MetaClient

logger = logging.getLogger("adpulse.report_engine")

class ReportEngine:
    @staticmethod
    def calculate_period_dates(
        periodicity: str,
        account_tz_str: str,
        reference_dt: datetime | None = None
    ) -> tuple[str, str, datetime]:
        """
        Calculates start and end dates (YYYY-MM-DD) according to the ad account's timezone.
        Returns (since_date, until_date, period_end_dt_in_tz).
        """
        try:
            tz = ZoneInfo(account_tz_str)
        except Exception:
            tz = ZoneInfo("UTC")

        now_in_tz = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
        today = now_in_tz.date()

        if periodicity == "daily":
            # Yesterday
            target_date = today - timedelta(days=1)
            since_date = target_date.isoformat()
            until_date = target_date.isoformat()
            period_end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=tz)

        elif periodicity == "weekly":
            # Previous full calendar week (Monday to Sunday)
            # weekday(): Monday is 0 and Sunday is 6
            days_since_monday = today.weekday()
            last_sunday = today - timedelta(days=days_since_monday + 1)
            last_monday = last_sunday - timedelta(days=6)
            since_date = last_monday.isoformat()
            until_date = last_sunday.isoformat()
            period_end_dt = datetime(last_sunday.year, last_sunday.month, last_sunday.day, 23, 59, 59, tzinfo=tz)

        elif periodicity == "monthly":
            # Previous full calendar month
            first_of_this_month = today.replace(day=1)
            last_of_prev_month = first_of_this_month - timedelta(days=1)
            first_of_prev_month = last_of_prev_month.replace(day=1)
            since_date = first_of_prev_month.isoformat()
            until_date = last_of_prev_month.isoformat()
            period_end_dt = datetime(
                last_of_prev_month.year, last_of_prev_month.month, last_of_prev_month.day,
                23, 59, 59, tzinfo=tz
            )
        else:
            # Default to yesterday
            target_date = today - timedelta(days=1)
            since_date = target_date.isoformat()
            until_date = target_date.isoformat()
            period_end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=tz)

        return since_date, until_date, period_end_dt

    @staticmethod
    def check_final_data_delay(
        period_end_dt: datetime,
        account_tz_str: str,
        delay_hours: int = 6
    ) -> tuple[bool, datetime]:
        """
        Verifies that at least `delay_hours` have elapsed since the period ended in account timezone.
        Returns (is_ready, ready_at_utc).
        """
        ready_at = period_end_dt + timedelta(hours=delay_hours)
        ready_at_utc = ready_at.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        is_ready = now_utc >= ready_at_utc
        return is_ready, ready_at_utc

    @staticmethod
    def compute_aggregated_metrics(insight_row: dict[str, Any]) -> dict[str, Any]:
        """
        Calculates all metric values from raw Meta insights.
        Sums additive values, and computes ratios strictly from totals. Never averages ratios.
        Returns None for metrics that cannot be obtained reliably or are not recorded.
        """
        if not insight_row:
            return {
                k: (0.0 if k in ("spend", "impressions", "reach", "clicks", "link_clicks", "ctr", "ctr_link") else None)
                for k in METRIC_DEFINITIONS
            }

        spend = float(insight_row.get("spend") or 0.0)
        impressions = int(insight_row.get("impressions") or 0)
        clicks = int(insight_row.get("clicks") or 0)
        link_clicks = int(insight_row.get("inline_link_clicks") or 0)
        reach = int(insight_row.get("reach") or 0)

        # Parse actions array
        actions_list = insight_row.get("actions", []) or []
        actions_map: dict[str, float] = {}
        for item in actions_list:
            act_type = item.get("action_type")
            act_val = float(item.get("value") or 0.0)
            actions_map[act_type] = actions_map.get(act_type, 0.0) + act_val

        # Parse action_values array (revenues)
        action_vals_list = insight_row.get("action_values", []) or []
        purchase_revenue = 0.0
        for item in action_vals_list:
            act_type = item.get("action_type")
            if act_type in ("purchase", "omni_purchase"):
                purchase_revenue += float(item.get("value") or 0.0)

        # 1. Leads
        # 'lead' in Meta is already the aggregate of on-Facebook and website leads
        if "lead" in actions_map:
            leads: int | None = int(actions_map["lead"])
        elif "onsite_conversion.lead_grouped" in actions_map or "offsite_conversion.fb_pixel_lead" in actions_map:
            leads = int(actions_map.get("onsite_conversion.lead_grouped", 0.0) + actions_map.get("offsite_conversion.fb_pixel_lead", 0.0))
        elif "leadgen.other" in actions_map:
            leads = int(actions_map["leadgen.other"])
        else:
            leads = None

        # 2. Messages (DM)
        # In Meta Marketing API, messaging conversations started is strictly 'onsite_conversion.messaging_conversation_started_7d'
        if "onsite_conversion.messaging_conversation_started_7d" in actions_map:
            messages: int | None = int(actions_map["onsite_conversion.messaging_conversation_started_7d"])
        else:
            messages = None

        # 3. Calls
        call_types = ["phone_call", "call_confirm", "onsite_conversion.call_attempt"]
        recorded_calls = [actions_map[k] for k in call_types if k in actions_map]
        calls: int | None = int(max(recorded_calls)) if recorded_calls else None

        # 4. App installs
        if "mobile_app_install" in actions_map:
            app_installs: int | None = int(actions_map["mobile_app_install"])
        elif "omni_app_install" in actions_map:
            app_installs = int(actions_map["omni_app_install"])
        elif "app_custom_event.fb_mobile_activate_app" in actions_map:
            app_installs = int(actions_map["app_custom_event.fb_mobile_activate_app"])
        else:
            app_installs = None

        # 5. Video views (ThruPlays)
        video_views: int | None = int(actions_map["video_thruplay_watched_actions"]) if "video_thruplay_watched_actions" in actions_map else None

        # 6. Post engagement
        post_engagement: int | None = int(actions_map["post_engagement"]) if "post_engagement" in actions_map else None

        # 7. Landing page views
        landing_page_views: int | None = int(actions_map["landing_page_view"]) if "landing_page_view" in actions_map else None

        # 8. Profile visits (limited support in Meta Marketing API)
        if "instagram_profile_visit" in actions_map:
            profile_visits: int | None = int(actions_map["instagram_profile_visit"])
        elif "onsite_conversion.messaging_user_profile_click" in actions_map:
            profile_visits = int(actions_map["onsite_conversion.messaging_user_profile_click"])
        else:
            profile_visits = None

        # 9. New followers
        # Meta Marketing API does NOT support Instagram follower metrics in Ads Insights.
        # Only Facebook Page likes ('like') or follows ('follow') are reported if present.
        if "like" in actions_map:
            new_followers: int | None = int(actions_map["like"])
        elif "follow" in actions_map:
            new_followers = int(actions_map["follow"])
        else:
            new_followers = None

        # Ratios (strictly computed from totals, never averaged; None if denominator is not positive or absent)
        ctr = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
        ctr_link = round((link_clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
        cpc = round((spend / clicks), 2) if clicks > 0 else (0.0 if spend == 0 else None)
        cpm = round((spend / impressions * 1000.0), 2) if impressions > 0 else (0.0 if spend == 0 else None)
        cpp = round((spend / reach * 1000.0), 2) if reach > 0 else (0.0 if spend == 0 else None)
        cpl = round((spend / leads), 2) if (leads is not None and leads > 0) else None
        cost_per_dm = round((spend / messages), 2) if (messages is not None and messages > 0) else None
        cost_per_call = round((spend / calls), 2) if (calls is not None and calls > 0) else None
        cost_per_install = round((spend / app_installs), 2) if (app_installs is not None and app_installs > 0) else None
        roas = round((purchase_revenue / spend), 2) if (spend > 0 and purchase_revenue > 0) else None

        return {
            "spend": round(spend, 2),
            "impressions": impressions,
            "reach": reach,
            "clicks": clicks,
            "link_clicks": link_clicks,
            "profile_visits": profile_visits,
            "landing_page_views": landing_page_views,
            "ctr": ctr,
            "ctr_link": ctr_link,
            "cpc": cpc,
            "cpm": cpm,
            "cpp": cpp,
            "new_followers": new_followers,
            "leads": leads,
            "cpl": cpl,
            "messages": messages,
            "cost_per_dm": cost_per_dm,
            "calls": calls,
            "cost_per_call": cost_per_call,
            "app_installs": app_installs,
            "cost_per_install": cost_per_install,
            "video_views": video_views,
            "post_engagement": post_engagement,
            "roas": roas
        }

    @staticmethod
    def build_telegram_message(
        report_name: str,
        account_name: str,
        currency: str,
        periodicity: str,
        since_date: str,
        until_date: str,
        selected_metrics: list[str],
        metric_values: dict[str, Any],
        custom_labels: dict[str, str] | None = None,
        lang: str = "ru"
    ) -> str:
        """Constructs a clean Telegram message."""
        default_labels = get_default_labels(lang)
        labels = {**default_labels, **(custom_labels or {})}

        period_title_map = {
            "daily": {"ru": "Ежедневный отчёт", "uz": "Kunlik hisobot", "en": "Daily Report"},
            "weekly": {"ru": "Еженедельный отчёт", "uz": "Haftalik hisobot", "en": "Weekly Report"},
            "monthly": {"ru": "Ежемесячный отчёт", "uz": "Oylik hisobot", "en": "Monthly Report"},
        }
        header_title = period_title_map.get(periodicity, period_title_map["daily"]).get(lang, "Daily Report")

        lines = [
            f"📊 <b>{header_title}: {report_name}</b>",
            f"🏢 <code>{account_name}</code> ({currency})",
            f"📅 <code>{since_date}</code>" if since_date == until_date else f"📅 <code>{since_date} — {until_date}</code>",
            ""
        ]

        # Check if spend is 0 and no impressions
        spend_val = metric_values.get("spend") or 0.0
        impr_val = metric_values.get("impressions") or 0
        if spend_val == 0.0 and impr_val == 0:
            lines.append("<i>ℹ️ За указанный период расходов и показов по выбранным кампаниям не зафиксировано.</i>")
            return "\n".join(lines)

        for key in selected_metrics:
            val = metric_values.get(key)
            defn = METRIC_DEFINITIONS.get(key)
            if not defn:
                continue

            label = labels.get(key, defn.ru_label)
            formatted_val = format_metric_value(val, defn.format_type, currency, lang=lang)
            lines.append(f"• <b>{label}</b>: <code>{formatted_val}</code>")

        return "\n".join(lines)

    @staticmethod
    def build_sheets_row_data(
        report_name: str,
        since_date: str,
        until_date: str,
        selected_metrics: list[str],
        metric_values: dict[str, Any],
        custom_labels: dict[str, str] | None = None,
        lang: str = "ru"
    ) -> tuple[list[str], list[Any]]:
        """
        Returns (header_labels, row_values) for appending into Google Sheets.
        Headers: ['Дата', 'Период', 'Отчёт', <metric labels...>]
        Values: numbers as numeric types, None as empty string "".
        """
        default_labels = get_default_labels(lang)
        labels = {**default_labels, **(custom_labels or {})}

        headers = ["Дата генерации", "Период", "Название отчёта"]
        period_str = since_date if since_date == until_date else f"{since_date} - {until_date}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        row: list[Any] = [now_str, period_str, report_name]

        for key in selected_metrics:
            label = labels.get(key, METRIC_DEFINITIONS.get(key, MetricDefinition(key=key, category="", is_additive=True, format_type="decimal", ru_label=key, uz_label=key, en_label=key, tooltip_ru="", tooltip_uz="", tooltip_en="")).ru_label)
            headers.append(label)
            val = metric_values.get(key)
            # Write numbers as numeric, None as empty cell
            row.append("" if val is None else val)

        return headers, row
