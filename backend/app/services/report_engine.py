import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

from app.services.meta_metrics import (
    METRIC_DEFINITIONS,
    MetricDefinition,
    format_metric_value,
    get_default_labels,
)

logger = logging.getLogger("adpulse.report_engine")


def round_money(val: float | int | Decimal | None) -> float | None:
    """Rounds currency amounts and cost per result metrics using Decimal ROUND_HALF_UP to 2 decimal places."""
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return round(float(val), 2)


class ReportEngine:
    @staticmethod
    def calculate_period_dates(
        periodicity: str,
        account_tz_str: str | None = None,
        reference_dt: datetime | None = None,
        is_test: bool = False
    ) -> tuple[str, str, datetime]:
        """
        Calculates start and end dates (YYYY-MM-DD) according to the ad account's timezone.
        Returns (since_date, until_date, period_end_dt_in_tz).
        When is_test=True, dynamically returns 'today' strictly in the ad account's timezone.
        For scheduled periods, period_end_dt is set to midnight of the next day (00:00:00),
        ensuring that adding FINAL_DATA_DELAY_HOURS (e.g. 6) gives exactly 06:00:00.
        """
        tz_target = account_tz_str or "Asia/Tashkent"
        try:
            tz = ZoneInfo(tz_target)
        except Exception:
            tz = ZoneInfo("Asia/Tashkent")

        now_in_tz = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
        today = now_in_tz.date()

        if is_test:
            # Dynamic date range for live/test reports: strictly TODAY in the ad account's timezone
            since_date = today.isoformat()
            until_date = today.isoformat()
            period_end_dt = datetime(
                today.year, today.month, today.day,
                now_in_tz.hour, now_in_tz.minute, now_in_tz.second,
                tzinfo=tz
            )
            return since_date, until_date, period_end_dt

        if periodicity == "daily":
            # Yesterday
            target_date = today - timedelta(days=1)
            since_date = target_date.isoformat()
            until_date = target_date.isoformat()
            # Period closes at midnight of the next day (00:00:00) so delay_hours=6 yields exactly 06:00:00
            period_end_dt = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz)

        elif periodicity == "weekly":
            # Previous full calendar week (Monday to Sunday)
            # weekday(): Monday is 0 and Sunday is 6
            days_since_monday = today.weekday()
            last_sunday = today - timedelta(days=days_since_monday + 1)
            last_monday = last_sunday - timedelta(days=6)
            since_date = last_monday.isoformat()
            until_date = last_sunday.isoformat()
            # Midnight immediately following Sunday (Monday 00:00:00)
            next_day_sunday = last_sunday + timedelta(days=1)
            period_end_dt = datetime(next_day_sunday.year, next_day_sunday.month, next_day_sunday.day, 0, 0, 0, tzinfo=tz)

        elif periodicity == "monthly":
            # Previous full calendar month
            first_of_this_month = today.replace(day=1)
            last_of_prev_month = first_of_this_month - timedelta(days=1)
            first_of_prev_month = last_of_prev_month.replace(day=1)
            since_date = first_of_prev_month.isoformat()
            until_date = last_of_prev_month.isoformat()
            # Midnight immediately following last of prev month (1st of this month 00:00:00)
            period_end_dt = datetime(
                first_of_this_month.year, first_of_this_month.month, first_of_this_month.day,
                0, 0, 0, tzinfo=tz
            )
        else:
            # Default to yesterday
            target_date = today - timedelta(days=1)
            since_date = target_date.isoformat()
            until_date = target_date.isoformat()
            period_end_dt = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz)

        return since_date, until_date, period_end_dt

    @staticmethod
    def calculate_comparison_dates(
        periodicity: str,
        account_tz_str: str | None = None,
        reference_dt: datetime | None = None,
        is_test: bool = False
    ) -> tuple[str, str, str | None, str | None, datetime]:
        """
        Calculates start and end dates (YYYY-MM-DD) for BOTH current and previous comparison periods
        strictly in the ad account's timezone.
        Returns (curr_since, curr_until, prev_since, prev_until, period_end_dt_in_tz).
        When is_test=True, prev_since and prev_until are None (no comparison for live runs).
        """
        tz_target = account_tz_str or "Asia/Tashkent"
        try:
            tz = ZoneInfo(tz_target)
        except Exception:
            tz = ZoneInfo("Asia/Tashkent")

        now_in_tz = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
        today = now_in_tz.date()

        if is_test:
            today_str = today.isoformat()
            period_end_dt = datetime(
                today.year, today.month, today.day,
                now_in_tz.hour, now_in_tz.minute, now_in_tz.second,
                tzinfo=tz
            )
            return today_str, today_str, None, None, period_end_dt

        if periodicity == "daily":
            curr_target = today - timedelta(days=1)
            prev_target = today - timedelta(days=2)
            curr_since = curr_target.isoformat()
            curr_until = curr_target.isoformat()
            prev_since = prev_target.isoformat()
            prev_until = prev_target.isoformat()
            period_end_dt = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz)

        elif periodicity == "weekly":
            days_since_monday = today.weekday()
            curr_last_sunday = today - timedelta(days=days_since_monday + 1)
            curr_last_monday = curr_last_sunday - timedelta(days=6)
            prev_last_sunday = curr_last_monday - timedelta(days=1)
            prev_last_monday = prev_last_sunday - timedelta(days=6)

            curr_since = curr_last_monday.isoformat()
            curr_until = curr_last_sunday.isoformat()
            prev_since = prev_last_monday.isoformat()
            prev_until = prev_last_sunday.isoformat()
            next_day_sunday = curr_last_sunday + timedelta(days=1)
            period_end_dt = datetime(next_day_sunday.year, next_day_sunday.month, next_day_sunday.day, 0, 0, 0, tzinfo=tz)

        elif periodicity == "monthly":
            first_of_this_month = today.replace(day=1)
            curr_last_day = first_of_this_month - timedelta(days=1)
            curr_first_day = curr_last_day.replace(day=1)
            prev_last_day = curr_first_day - timedelta(days=1)
            prev_first_day = prev_last_day.replace(day=1)

            curr_since = curr_first_day.isoformat()
            curr_until = curr_last_day.isoformat()
            prev_since = prev_first_day.isoformat()
            prev_until = prev_last_day.isoformat()
            period_end_dt = datetime(first_of_this_month.year, first_of_this_month.month, first_of_this_month.day, 0, 0, 0, tzinfo=tz)

        else:
            curr_target = today - timedelta(days=1)
            prev_target = today - timedelta(days=2)
            curr_since = curr_target.isoformat()
            curr_until = curr_target.isoformat()
            prev_since = prev_target.isoformat()
            prev_until = prev_target.isoformat()
            period_end_dt = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz)

        return curr_since, curr_until, prev_since, prev_until, period_end_dt

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
    def compute_aggregated_metrics(
        insight_row: dict[str, Any],
        campaign_insights: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Calculates all metric values from raw Meta insights.
        Sums additive values, and computes ratios strictly from totals. Never averages ratios.
        When campaign_insights is provided, uses hybrid extraction for campaign-level indicators
        (such as total_profile_visits in results) while reach is always taken strictly from account level.
        Returns None for metrics that cannot be obtained reliably or are not recorded.
        """
        if not insight_row:
            empty_res = {
                k: (0.0 if k in ("spend", "impressions", "reach", "clicks", "link_clicks", "ctr", "ctr_link") else None)
                for k in METRIC_DEFINITIONS
            }
            empty_res["approximate_metrics"] = []
            return empty_res

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

        # Parse action_values array (revenues) - deduplicating omni_purchase and purchase
        action_vals_list = insight_row.get("action_values", []) or []
        action_vals_map: dict[str, float] = {}
        for item in action_vals_list:
            act_type = item.get("action_type")
            act_val = float(item.get("value") or 0.0)
            if act_type:
                action_vals_map[act_type] = act_val

        # Meta includes on-site and website purchases in omni_purchase.
        # Prioritize omni_purchase, then purchase, then offsite fb_pixel_purchase to prevent double counting.
        if "omni_purchase" in action_vals_map:
            purchase_revenue = action_vals_map["omni_purchase"]
        elif "purchase" in action_vals_map:
            purchase_revenue = action_vals_map["purchase"]
        elif "offsite_conversion.fb_pixel_purchase" in action_vals_map:
            purchase_revenue = action_vals_map["offsite_conversion.fb_pixel_purchase"]
        else:
            custom_purchases = [
                v for k, v in action_vals_map.items()
                if "purchase" in k.lower()
            ]
            purchase_revenue = max(custom_purchases) if custom_purchases else 0.0

        # Parse cost_per_action_type array
        cost_per_action_list = insight_row.get("cost_per_action_type", []) or []
        cost_per_action_map: dict[str, float] = {}
        for item in cost_per_action_list:
            act_type = item.get("action_type")
            cost_per_action_map[act_type] = float(item.get("value") or 0.0)

        # 3. Calls ("Qo'ng'iroqlar")
        # In Meta Ads Manager, 'Calls placed' / Click-to-call is recorded under:
        # 'click_to_call_native_call_placed' (primary "Calls placed" event),
        # phone call events, or fallback to 'onsite_conversion.lead_grouped'.
        call_types = [
            "click_to_call_native_call_placed",
            "phone_call",
            "call_confirm",
            "onsite_conversion.call_attempt",
            "click_to_call",
            "click_to_call_call_confirm",
            "phone_call_clicks",
            "contact_total",
        ]
        calls_is_approximate = False
        if "click_to_call_native_call_placed" in actions_map:
            calls: int | None = int(actions_map["click_to_call_native_call_placed"])
        else:
            specific_calls = [actions_map[k] for k in call_types if k in actions_map]
            if specific_calls:
                calls = int(max(specific_calls))
            elif "onsite_conversion.lead_grouped" in actions_map and ("lead" not in actions_map or actions_map.get("lead", 0) == 0):
                # In Click-to-call / Call campaigns, Meta groups call leads under onsite_conversion.lead_grouped (fallback)
                calls = int(actions_map["onsite_conversion.lead_grouped"])
                calls_is_approximate = True
            else:
                custom_calls = [
                    v for k, v in actions_map.items()
                    if any(x in k.lower() for x in ("call", "click_to_call"))
                ]
                calls = int(max(custom_calls)) if custom_calls else None

        # 1. Leads
        # 'lead' in Meta is already the aggregate of on-Facebook and website leads
        if "lead" in actions_map:
            leads: int | None = int(actions_map["lead"])
        elif "offsite_conversion.fb_pixel_lead" in actions_map:
            leads = int(actions_map["offsite_conversion.fb_pixel_lead"])
        elif "leadgen.other" in actions_map:
            leads = int(actions_map["leadgen.other"])
        elif "onsite_conversion.lead_grouped" in actions_map and calls is None:
            leads = int(actions_map["onsite_conversion.lead_grouped"])
        else:
            leads = None

        # 2. Messages (DM)
        # In Meta Marketing API, messaging conversations started is strictly 'onsite_conversion.messaging_conversation_started_7d'
        if "onsite_conversion.messaging_conversation_started_7d" in actions_map:
            messages: int | None = int(actions_map["onsite_conversion.messaging_conversation_started_7d"])
        else:
            messages = None

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

        # 8. Profile visits ("Profil tashriflari" / Profile and Page visits)
        # Hybrid two-layer extraction:
        # At account level, Meta API returns results: null or [{indicator: "mixed"}], omitting total_profile_visits.
        # When campaign_insights is available, we extract and sum total_profile_visits strictly from campaigns that report it.
        # If no campaign reports total_profile_visits, we fall back to recorded profile actions, link_click or inline_link_clicks with '≈'.
        campaign_profile_visits = 0
        found_campaign_profile_visits = False

        if campaign_insights:
            for camp in campaign_insights:
                for res_item in (camp.get("results", []) or []):
                    ind = res_item.get("indicator")
                    if ind in ("total_profile_visits", "profile_visit", "actions:profile_visit"):
                        vals = res_item.get("values", [])
                        if vals and vals[0].get("value") is not None:
                            try:
                                campaign_profile_visits += int(float(vals[0]["value"]))
                                found_campaign_profile_visits = True
                                break
                            except (ValueError, TypeError):
                                pass

        # Also check account-level results array if available
        results_list = insight_row.get("results", []) or []
        api_profile_visits = None
        for res_item in results_list:
            ind = res_item.get("indicator")
            if ind in ("total_profile_visits", "profile_visit", "actions:profile_visit"):
                vals = res_item.get("values", [])
                if vals and vals[0].get("value") is not None:
                    try:
                        api_profile_visits = int(float(vals[0]["value"]))
                        break
                    except (ValueError, TypeError):
                        pass

        profile_action_keys = [
            "profile_visit",
            "instagram_profile_visit",
            "page_visit",
            "onsite_conversion.messaging_user_profile_click",
            "profile_view",
        ]
        recorded_profile_visits = [actions_map[k] for k in profile_action_keys if k in actions_map]
        profile_visits_is_approximate = False

        if found_campaign_profile_visits:
            # Strictly sum campaigns with total_profile_visits without adding link_clicks
            profile_visits: int | None = campaign_profile_visits
            profile_visits_is_approximate = False
        elif api_profile_visits is not None:
            profile_visits = api_profile_visits
            profile_visits_is_approximate = False
        elif recorded_profile_visits:
            profile_visits = int(max(recorded_profile_visits))
            profile_visits_is_approximate = False
        else:
            # Fallback when total_profile_visits indicator is absent.
            # Strictly differentiate page_view and landing_page_view: landing_page_view must NEVER match page_view.
            def _is_profile_action(k_str: str) -> bool:
                k_low = k_str.lower()
                if "landing_page_view" in k_low:
                    return False
                return (
                    any(x in k_low for x in ("profile_visit", "page_visit", "profile_click"))
                    or k_low == "page_view"
                    or k_low.endswith(".page_view")
                )

            custom_profile_actions = [
                v for k, v in actions_map.items()
                if _is_profile_action(k)
            ]
            if custom_profile_actions:
                profile_visits = int(max(custom_profile_actions))
                profile_visits_is_approximate = False
            elif "link_click" in actions_map and actions_map["link_click"] > 0:
                profile_visits = int(actions_map["link_click"])
                profile_visits_is_approximate = True
            elif link_clicks > 0:
                profile_visits = int(link_clicks)
                profile_visits_is_approximate = True
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
        cpc = round_money(spend / clicks) if clicks > 0 else (0.0 if spend == 0 else None)
        cpm = round_money(spend / impressions * 1000.0) if impressions > 0 else (0.0 if spend == 0 else None)
        cpp = round_money(spend / reach * 1000.0) if reach > 0 else (0.0 if spend == 0 else None)
        cpl = round_money(spend / leads) if (leads is not None and leads > 0) else None
        cost_per_dm = round_money(spend / messages) if (messages is not None and messages > 0) else None

        # Cost per call: check cost_per_action_type or compute spend / calls
        call_cost_keys = [
            "click_to_call_native_call_placed",
            "phone_call", "call_confirm", "onsite_conversion.call_attempt",
            "click_to_call", "click_to_call_call_confirm", "phone_call_clicks",
            "contact_total", "onsite_conversion.lead_grouped"
        ]
        cost_per_call = None
        for ck in call_cost_keys:
            if ck in cost_per_action_map and cost_per_action_map[ck] > 0:
                cost_per_call = round_money(cost_per_action_map[ck])
                break
        if cost_per_call is None and calls is not None and calls > 0 and spend > 0:
            cost_per_call = round_money(spend / calls)

        cost_per_install = round_money(spend / app_installs) if (app_installs is not None and app_installs > 0) else None

        # Check purchase_roas array from Meta API
        purchase_roas_list = insight_row.get("purchase_roas", []) or []
        roas_map: dict[str, float] = {}
        for item in purchase_roas_list:
            act_type = item.get("action_type")
            act_val = float(item.get("value") or 0.0)
            if act_type:
                roas_map[act_type] = act_val

        api_roas = None
        if "omni_purchase" in roas_map:
            api_roas = roas_map["omni_purchase"]
        elif "purchase" in roas_map:
            api_roas = roas_map["purchase"]
        elif roas_map:
            api_roas = next(iter(roas_map.values()))

        if api_roas is not None and api_roas > 0:
            roas = round_money(api_roas)
        elif spend > 0 and purchase_revenue > 0:
            roas = round_money(purchase_revenue / spend)
        else:
            roas = None

        approximate_metrics: list[str] = []
        if calls is not None and calls_is_approximate:
            approximate_metrics.append("calls")
            if cost_per_call is not None:
                approximate_metrics.append("cost_per_call")
        if profile_visits is not None and profile_visits_is_approximate:
            approximate_metrics.append("profile_visits")

        return {
            "spend": round_money(spend) or 0.0,
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
            "roas": roas,
            "approximate_metrics": approximate_metrics
        }

    @staticmethod
    def calculate_metrics_deltas(
        current_metrics: dict[str, Any],
        previous_metrics: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        """
        Calculates percentage deltas and formatted badge strings for each metric comparing current vs previous period.
        - Suppresses deltas whenever the metric was resolved via fallback (approximate) in either period.
        - Computes ratio deltas strictly from unrounded raw values to prevent distortion.
        - Suppresses delta when data is missing in current period (never outputs -100%).
        - spend, impressions, reach, clicks are neutral (▲/▼ without 🟢/🔴).
        """
        deltas: dict[str, dict[str, Any]] = {}
        if not previous_metrics:
            return deltas

        curr_approx = set(current_metrics.get("approximate_metrics") or [])
        prev_approx = set(previous_metrics.get("approximate_metrics") or [])

        neutral_metrics = {"spend", "impressions", "reach", "clicks"}
        lower_is_better = {"cpc", "cpm", "cpp", "cpl", "cost_per_dm", "cost_per_call", "cost_per_install"}

        for key in METRIC_DEFINITIONS:
            curr_val = current_metrics.get(key)
            prev_val = previous_metrics.get(key)

            if curr_val is None and prev_val is None:
                continue

            # Suppress delta for approximate metrics in either period
            if (key in curr_approx) != (key in prev_approx):
                deltas[key] = {
                    "status": "mixed_fallback",
                    "diff_pct": None,
                    "badge": None,
                    "curr": curr_val,
                    "prev": prev_val
                }
                continue
            elif key in curr_approx and key in prev_approx:
                deltas[key] = {
                    "status": "approximate_suppressed",
                    "diff_pct": None,
                    "badge": None,
                    "curr": curr_val,
                    "prev": prev_val
                }
                continue

            # If current value is missing, do not show -100%
            if curr_val is None:
                deltas[key] = {
                    "status": "no_data",
                    "diff_pct": None,
                    "badge": None,
                    "curr": None,
                    "prev": prev_val
                }
                continue

            # If previous value is missing or zero
            if prev_val is None or prev_val == 0:
                if curr_val > 0:
                    deltas[key] = {
                        "status": "new",
                        "diff_pct": None,
                        "badge": "🆕 new",
                        "curr": curr_val,
                        "prev": prev_val
                    }
                else:
                    deltas[key] = {
                        "status": "no_change",
                        "diff_pct": 0.0,
                        "badge": "= 0%",
                        "curr": curr_val,
                        "prev": prev_val
                    }
                continue

            # Precise unrounded ratios to prevent distortion from pre-rounding
            calc_curr = curr_val
            calc_prev = prev_val

            unrounded_curr = None
            unrounded_prev = None

            if key == "cpc":
                c_sp, c_cl = current_metrics.get("spend"), current_metrics.get("clicks")
                p_sp, p_cl = previous_metrics.get("spend"), previous_metrics.get("clicks")
                if c_sp is not None and c_cl and p_sp is not None and p_cl:
                    unrounded_curr = c_sp / c_cl
                    unrounded_prev = p_sp / p_cl
            elif key == "cpm":
                c_sp, c_im = current_metrics.get("spend"), current_metrics.get("impressions")
                p_sp, p_im = previous_metrics.get("spend"), previous_metrics.get("impressions")
                if c_sp is not None and c_im and p_sp is not None and p_im:
                    unrounded_curr = (c_sp / c_im) * 1000.0
                    unrounded_prev = (p_sp / p_im) * 1000.0
            elif key == "cpp":
                c_sp, c_re = current_metrics.get("spend"), current_metrics.get("reach")
                p_sp, p_re = previous_metrics.get("spend"), previous_metrics.get("reach")
                if c_sp is not None and c_re and p_sp is not None and p_re:
                    unrounded_curr = (c_sp / c_re) * 1000.0
                    unrounded_prev = (p_sp / p_re) * 1000.0
            elif key == "ctr":
                c_cl, c_im = current_metrics.get("clicks"), current_metrics.get("impressions")
                p_cl, p_im = previous_metrics.get("clicks"), previous_metrics.get("impressions")
                if c_cl is not None and c_im and p_cl is not None and p_im:
                    unrounded_curr = (c_cl / c_im) * 100.0
                    unrounded_prev = (p_cl / p_im) * 100.0
            elif key == "ctr_link":
                c_lc, c_im = current_metrics.get("link_clicks"), current_metrics.get("impressions")
                p_lc, p_im = previous_metrics.get("link_clicks"), previous_metrics.get("impressions")
                if c_lc is not None and c_im and p_lc is not None and p_im:
                    unrounded_curr = (c_lc / c_im) * 100.0
                    unrounded_prev = (p_lc / p_im) * 100.0
            elif key == "cpl":
                c_sp, c_ld = current_metrics.get("spend"), current_metrics.get("leads")
                p_sp, p_ld = previous_metrics.get("spend"), previous_metrics.get("leads")
                if c_sp is not None and c_ld and p_sp is not None and p_ld:
                    unrounded_curr = c_sp / c_ld
                    unrounded_prev = p_sp / p_ld
            elif key == "cost_per_dm":
                c_sp, c_msg = current_metrics.get("spend"), current_metrics.get("messages")
                p_sp, p_msg = previous_metrics.get("spend"), previous_metrics.get("messages")
                if c_sp is not None and c_msg and p_sp is not None and p_msg:
                    unrounded_curr = c_sp / c_msg
                    unrounded_prev = p_sp / p_msg
            elif key == "cost_per_call":
                c_sp, c_ca = current_metrics.get("spend"), current_metrics.get("calls")
                p_sp, p_ca = previous_metrics.get("spend"), previous_metrics.get("calls")
                if c_sp is not None and c_ca and p_sp is not None and p_ca:
                    unrounded_curr = c_sp / c_ca
                    unrounded_prev = p_sp / p_ca
            elif key == "roas":
                c_rev, c_sp = current_metrics.get("purchase_revenue"), current_metrics.get("spend")
                p_rev, p_sp = previous_metrics.get("purchase_revenue"), previous_metrics.get("spend")
                if c_rev is not None and c_sp and p_rev is not None and p_sp:
                    unrounded_curr = c_rev / c_sp
                    unrounded_prev = p_rev / p_sp

            # If unrounded values are within rounding tolerance (<= 0.02) of curr_val / prev_val, use them
            if unrounded_curr is not None and unrounded_prev is not None:
                if abs(curr_val - unrounded_curr) <= 0.02 and abs(prev_val - unrounded_prev) <= 0.02:
                    calc_curr = unrounded_curr
                    calc_prev = unrounded_prev

            # Standard delta calculation from precise values
            pct_raw = ((calc_curr - calc_prev) / abs(calc_prev)) * 100.0

            # Check exact equality: «= 0%» только при точном равенстве
            if calc_curr == calc_prev or pct_raw == 0.0:
                badge = "= 0%"
                diff_pct = 0.0
            elif abs(pct_raw) < 1.0:
                # Requirement: для |Δ| меньше 1% показывать одну десятичную (−0.5%, +0.3%)
                diff_pct = float(Decimal(str(pct_raw)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
                if diff_pct == 0.0:
                    diff_pct = 0.1 if pct_raw > 0 else -0.1

                if diff_pct > 0:
                    sign_str = f"▲ +{diff_pct:.1f}%"
                    if key in neutral_metrics:
                        badge = sign_str
                    elif key in lower_is_better:
                        badge = f"🔴 {sign_str}"  # cost increased
                    else:
                        badge = f"🟢 {sign_str}"  # conversion/result increased
                else:
                    sign_str = f"▼ {diff_pct:.1f}%"
                    if key in neutral_metrics:
                        badge = sign_str
                    elif key in lower_is_better:
                        badge = f"🟢 {sign_str}"  # cost decreased
                    else:
                        badge = f"🔴 {sign_str}"  # conversion/result decreased
            else:
                diff_pct = float(Decimal(str(pct_raw)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
                # Requirement: .5 округлять от нуля (−12.5 → −13, +12.5 → +13)
                pct_int = int(Decimal(str(pct_raw)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if pct_int > 0:
                    sign_str = f"▲ +{pct_int}%"
                    if key in neutral_metrics:
                        badge = sign_str
                    elif key in lower_is_better:
                        badge = f"🔴 {sign_str}"  # cost increased
                    else:
                        badge = f"🟢 {sign_str}"  # conversion/result increased
                else:
                    sign_str = f"▼ {pct_int}%"
                    if key in neutral_metrics:
                        badge = sign_str
                    elif key in lower_is_better:
                        badge = f"🟢 {sign_str}"  # cost decreased
                    else:
                        badge = f"🔴 {sign_str}"  # conversion/result decreased

            deltas[key] = {
                "status": "compared",
                "diff_pct": diff_pct,
                "badge": badge,
                "curr": curr_val,
                "prev": prev_val
            }

        return deltas

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
        lang: str = "ru",
        template_type: str | None = None,
        is_test: bool = False,
        account_timezone: str | None = None,
        as_of_time: str | None = None,
        deltas: dict[str, dict[str, Any]] | None = None,
        prev_period_info: tuple[str, str] | None = None
    ) -> str:
        """Constructs a clean Telegram message without deltas."""
        default_labels = get_default_labels(lang)
        labels = {**default_labels, **(custom_labels or {})}

        period_title_map = {
            "daily": {"ru": "Ежедневный отчёт", "uz": "Kunlik hisobot", "en": "Daily Report"},
            "weekly": {"ru": "Еженедельный отчёт", "uz": "Haftalik hisobot", "en": "Weekly Report"},
            "monthly": {"ru": "Ежемесячный отчёт", "uz": "Oylik hisobot", "en": "Monthly Report"},
        }
        if is_test:
            period_title_map = {
                "daily": {"ru": "Ежедневный отчёт (LIVE)", "uz": "Kunlik hisobot (LIVE)", "en": "Daily Report (LIVE)"},
                "weekly": {"ru": "Еженедельный отчёт (LIVE)", "uz": "Haftalik hisobot (LIVE)", "en": "Weekly Report (LIVE)"},
                "monthly": {"ru": "Ежемесячный отчёт (LIVE)", "uz": "Oylik hisobot (LIVE)", "en": "Monthly Report (LIVE)"},
            }
        header_title = period_title_map.get(periodicity, period_title_map["daily"]).get(lang, "Daily Report")

        # Select header emoji based on template_type or metric composition
        emoji_map = {
            "daily_pulse": "📊",
            "pulse": "📊",
            "lead_generation": "🎯",
            "leads": "🎯",
            "direct_messages": "💬",
            "messages": "💬",
            "brand_awareness": "👁",
            "awareness": "👁",
        }
        if template_type and template_type in emoji_map:
            header_emoji = emoji_map[template_type]
        elif "leads" in selected_metrics or "cpl" in selected_metrics:
            header_emoji = "🎯"
        elif "messages" in selected_metrics or "cost_per_dm" in selected_metrics:
            header_emoji = "💬"
        elif "reach" in selected_metrics and "impressions" in selected_metrics and "spend" in selected_metrics and len(selected_metrics) <= 5 and "leads" not in selected_metrics and "messages" not in selected_metrics and "clicks" not in selected_metrics:
            header_emoji = "👁"
        else:
            header_emoji = "📊"

        tz_display = f" • {account_timezone}" if account_timezone else ""
        account_line = f"🏢 <code>{account_name}</code> ({currency}{tz_display})"

        date_line = f"📅 <code>{since_date}</code>" if since_date == until_date else f"📅 <code>{since_date} — {until_date}</code>"
        if is_test:
            if not as_of_time:
                try:
                    tz = ZoneInfo(account_timezone) if account_timezone else ZoneInfo("Asia/Tashkent")
                except Exception:
                    tz = ZoneInfo("Asia/Tashkent")
                as_of_time = datetime.now(tz).strftime("%H:%M")
            test_note_map = {
                "ru": f"данные на {as_of_time}, неполные",
                "uz": f"soat {as_of_time} holatiga ko'ra, to'liq emas",
                "en": f"data as of {as_of_time}, incomplete",
            }
            test_note = test_note_map.get(lang, test_note_map["ru"])
            date_line += f" ({test_note})"

        lines = [
            f"{header_emoji} <b>{header_title}: {report_name}</b>",
            account_line,
            date_line,
            ""
        ]

        # Check if spend is 0 and no impressions
        spend_val = metric_values.get("spend") or 0.0
        impr_val = metric_values.get("impressions") or 0
        if spend_val == 0.0 and impr_val == 0:
            no_data_map = {
                "ru": "<i>ℹ️ За указанный период расходов и показов по выбранным кампаниям не зафиксировано.</i>",
                "uz": "<i>ℹ️ Tanlangan davr uchun ko'rsatilgan kampaniyalar bo'yicha xarajat va taassurotlar qayd etilmadi.</i>",
                "en": "<i>ℹ️ No spend or impressions recorded for the selected campaigns during this period.</i>",
            }
            lines.append(no_data_map.get(lang, no_data_map["ru"]))
            return "\n".join(lines)

        approximate_metrics = metric_values.get("approximate_metrics") or []
        for key in selected_metrics:
            val = metric_values.get(key)
            defn = METRIC_DEFINITIONS.get(key)
            if not defn:
                continue

            label = labels.get(key, defn.ru_label)
            is_approx = key in approximate_metrics
            formatted_val = format_metric_value(val, defn.format_type, currency, lang=lang, is_approximate=is_approx)
            # Message 1 is clean without deltas
            lines.append(f"• <b>{label}</b>: <code>{formatted_val}</code>")

        return "\n".join(lines)

    @staticmethod
    def build_comparison_message(
        report_name: str,
        account_name: str,
        currency: str,
        periodicity: str,
        curr_since: str,
        curr_until: str,
        prev_since: str,
        prev_until: str,
        selected_metrics: list[str],
        curr_metric_values: dict[str, Any],
        prev_metric_values: dict[str, Any],
        deltas: dict[str, dict[str, Any]],
        custom_labels: dict[str, str] | None = None,
        lang: str = "ru",
        account_timezone: str | None = None
    ) -> str:
        """
        Builds the second separate comparison message ('was → became') grouped by blocks:
        1. General metrics (Общие показатели / Umumiy ko'rsatkichlar)
        2. Efficiency (Эффективность / Samaradorlik)
        3. Conversions & Cost (Конверсии и стоимость / Konversiyalar va narx)
        """
        default_labels = get_default_labels(lang)
        labels = {**default_labels, **(custom_labels or {})}

        titles = {
            "ru": f"⚖️ <b>Сравнение с прошлым периодом: {report_name}</b>",
            "uz": f"⚖️ <b>O'tgan davr bilan solishtirish: {report_name}</b>",
            "en": f"⚖️ <b>Period Comparison: {report_name}</b>"
        }
        header_title = titles.get(lang, titles["ru"])

        curr_dates = curr_since if curr_since == curr_until else f"{curr_since} — {curr_until}"
        prev_dates = prev_since if prev_since == prev_until else f"{prev_since} — {prev_until}"
        date_line = f"📅 <code>{prev_dates}</code> → <code>{curr_dates}</code>"

        if periodicity == "monthly":
            try:
                curr_d1 = datetime.fromisoformat(curr_since)
                curr_d2 = datetime.fromisoformat(curr_until)
                prev_d1 = datetime.fromisoformat(prev_since)
                prev_d2 = datetime.fromisoformat(prev_until)
                curr_days = (curr_d2 - curr_d1).days + 1
                prev_days = (prev_d2 - prev_d1).days + 1
                month_notes = {
                    "ru": f" ({prev_days} дн. → {curr_days} дн.)",
                    "uz": f" ({prev_days} kun → {curr_days} kun)",
                    "en": f" ({prev_days} days → {curr_days} days)",
                }
                date_line += month_notes.get(lang, month_notes["ru"])
            except Exception:
                pass

        lines = [
            header_title,
            date_line,
            ""
        ]

        # Metric Blocks Definition
        block_defs = [
            {
                "id": "general",
                "titles": {
                    "ru": "📈 <b>Общие показатели:</b>",
                    "uz": "📈 <b>Umumiy ko'rsatkichlar:</b>",
                    "en": "📈 <b>General Metrics:</b>"
                },
                "keys": ["spend", "reach", "impressions", "clicks"]
            },
            {
                "id": "efficiency",
                "titles": {
                    "ru": "⚡ <b>Эффективность:</b>",
                    "uz": "⚡ <b>Samaradorlik:</b>",
                    "en": "⚡ <b>Efficiency:</b>"
                },
                "keys": ["ctr", "ctr_link", "cpc", "cpm", "cpp"]
            },
            {
                "id": "conversions",
                "titles": {
                    "ru": "🎯 <b>Конверсии и стоимость:</b>",
                    "uz": "🎯 <b>Konversiyalar va narx:</b>",
                    "en": "🎯 <b>Conversions & Cost:</b>"
                },
                "keys": [
                    "leads", "cpl", "messages", "cost_per_dm", "calls", "cost_per_call",
                    "profile_visits", "new_followers", "roas", "purchase_revenue",
                    "mobile_app_install", "cost_per_install", "landing_page_views",
                    "video_thruplay_watched_actions", "post_engagement"
                ]
            }
        ]

        curr_approx = set(curr_metric_values.get("approximate_metrics") or [])
        prev_approx = set(prev_metric_values.get("approximate_metrics") or [])

        blocks_added = 0
        for block in block_defs:
            block_keys = [k for k in block["keys"] if k in selected_metrics]
            if not block_keys:
                continue

            block_lines = []
            for key in block_keys:
                defn = METRIC_DEFINITIONS.get(key)
                if not defn:
                    continue

                label = labels.get(key, defn.ru_label)
                c_val = curr_metric_values.get(key)
                p_val = prev_metric_values.get(key)

                # Skip row when both values are missing/None (never output "н/д → н/д")
                if c_val is None and p_val is None:
                    continue

                is_curr_approx = key in curr_approx
                is_prev_approx = key in prev_approx

                formatted_prev = format_metric_value(p_val, defn.format_type, currency, lang=lang, is_approximate=is_prev_approx)
                formatted_curr = format_metric_value(c_val, defn.format_type, currency, lang=lang, is_approximate=is_curr_approx)

                badge_str = ""
                # Do NOT show badge if either value is approximate, or if current value is missing (val -> н/д stays without percentage)
                if not (is_curr_approx or is_prev_approx) and deltas and key in deltas and c_val is not None:
                    badge = deltas[key].get("badge")
                    if badge:
                        badge_str = f" {badge}"

                block_lines.append(f"• <b>{label}</b>: <code>{formatted_prev}</code> → <code>{formatted_curr}</code>{badge_str}")

            if block_lines:
                if blocks_added > 0:
                    lines.append("")
                lines.append(block["titles"].get(lang, block["titles"]["ru"]))
                lines.extend(block_lines)
                blocks_added += 1

        return "\n".join(lines)

    @staticmethod
    def build_sheets_row_data(
        report_name: str,
        since_date: str,
        until_date: str,
        selected_metrics: list[str],
        metric_values: dict[str, Any],
        custom_labels: dict[str, str] | None = None,
        lang: str = "ru",
        deltas: dict[str, dict[str, Any]] | None = None
    ) -> tuple[list[str], list[Any]]:
        """
        Returns (header_labels, row_values) for appending into Google Sheets.
        Headers: ['Дата генерации', 'Период', 'Название отчёта', <metric labels...>, <delta labels...>]
        Values: numbers as numeric types, None as empty string "".
        Deltas are formatted as numeric floats (e.g. 12.5 or -4.0), allowing formulas and charting.
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

        if deltas is not None:
            for key in selected_metrics:
                label = labels.get(key, METRIC_DEFINITIONS.get(key, MetricDefinition(key=key, category="", is_additive=True, format_type="decimal", ru_label=key, uz_label=key, en_label=key, tooltip_ru="", tooltip_uz="", tooltip_en="")).ru_label)
                headers.append(f"Δ {label} (%)")
                delta_info = deltas.get(key)
                if delta_info and delta_info.get("diff_pct") is not None:
                    row.append(delta_info["diff_pct"])
                else:
                    row.append("")

        return headers, row
