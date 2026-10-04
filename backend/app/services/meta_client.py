import asyncio
from datetime import datetime, timezone
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("adpulse.meta_client")

DEFAULT_USE_ACCOUNT_ATTRIBUTION_SETTING: bool = getattr(settings, "META_USE_ACCOUNT_ATTRIBUTION_SETTING", True)

def is_meta_rate_limit(err_code: int | None, is_transient: bool = False) -> bool:
    """Identifies standard Meta Marketing API rate limit and throttling error codes."""
    if err_code is None:
        return False
    if err_code in (4, 17, 32, 613):
        return True
    if 80000 <= err_code <= 80099:
        return True
    return is_transient


class MetaAPIError(Exception):
    def __init__(self, message: str, code: int | None = None, subcode: int | None = None, is_auth_error: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.subcode = subcode
        self.is_auth_error = is_auth_error

class MetaTokenExpiredError(MetaAPIError):
    pass

class MetaClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = settings.META_GRAPH_API_BASE

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3
    ) -> dict[str, Any]:
        """Executes HTTP request to Meta Graph API with exponential backoff for rate limits."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        query_params = (params or {}).copy()
        query_params["access_token"] = self.access_token

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(method, url, params=query_params)
                    data = response.json()

                    if "error" in data:
                        err = data["error"]
                        err_code = err.get("code")
                        err_subcode = err.get("error_subcode")
                        err_msg = err.get("message", "Unknown Meta API error")
                        is_transient = bool(err.get("is_transient"))

                        # Code 190: Invalid or expired OAuth access token
                        if err_code == 190:
                            logger.warning(f"Meta token expired or invalid (code {err_code}, subcode {err_subcode}): {err_msg}")
                            raise MetaTokenExpiredError(
                                f"Токен Meta устарел или недействителен (код {err_code}). Пожалуйста, обновите токен.",
                                code=err_code,
                                subcode=err_subcode,
                                is_auth_error=True
                            )

                        # Codes 4, 17, 32, 613, 80000+ or transient: Rate limit exceeded -> retry with exponential backoff
                        if is_meta_rate_limit(err_code, is_transient) and attempt < max_retries:
                            logger.info(f"Meta rate limit hit (code {err_code}), backing off {delay}s (attempt {attempt}/{max_retries})")
                            await asyncio.sleep(delay)
                            delay *= 2
                            continue

                        # Permissions / ads_read missing
                        if err_code in (200, 294, 10):
                            raise MetaAPIError(
                                f"Ошибка прав доступа: {err_msg}. Убедитесь, что токен имеет право 'ads_read' и доступ к рекламному аккаунту.",
                                code=err_code,
                                subcode=err_subcode
                            )

                        raise MetaAPIError(f"Ошибка Meta Graph API: {err_msg}", code=err_code, subcode=err_subcode)

                    return data
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < max_retries:
                    logger.warning(f"Network error communicating with Meta API: {exc}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                raise MetaAPIError(f"Ошибка соединения с серверами Meta: {exc}")

        raise MetaAPIError("Превышено количество попыток запроса к Meta API")

    async def verify_token(self) -> dict[str, Any]:
        """Validates token by querying /me and verifies ad account access."""
        data = await self._make_request("GET", "/me", params={"fields": "id,name,picture.type(large)"})
        user_id = data.get("id")
        user_name = data.get("name", "Meta System User")
        avatar_url = None
        if "picture" in data and "data" in data["picture"]:
            avatar_url = data["picture"]["data"].get("url")

        # Also verify advertising permissions (ads_read)
        try:
            await self._make_request("GET", "/me/adaccounts", params={"fields": "id", "limit": "1"})
        except MetaTokenExpiredError:
            raise
        except MetaAPIError as e:
            if e.code in (200, 294, 10):
                raise MetaAPIError(
                    "Токен не имеет прав для чтения рекламных аккаунтов (ads_read). Убедитесь, что токен создан с нужными правами.",
                    code=e.code
                )
        except Exception:
            pass

        return {
            "meta_user_id": user_id,
            "meta_user_name": user_name,
            "meta_avatar_url": avatar_url,
            "is_valid": True
        }

    async def get_ad_accounts(self) -> list[dict[str, Any]]:
        """Fetches all ad accounts accessible with the token, handling pagination."""
        accounts: list[dict[str, Any]] = []
        endpoint = "/me/adaccounts"
        params = {
            "fields": "id,name,account_id,currency,timezone_name,account_status,business_name",
            "limit": "100"
        }

        while True:
            data = await self._make_request("GET", endpoint, params=params)
            rows = data.get("data", [])
            for row in rows:
                accounts.append({
                    "id": row.get("id"),  # e.g. "act_123456789"
                    "account_id": row.get("account_id"),
                    "name": row.get("name") or f"Account {row.get('account_id')}",
                    "currency": row.get("currency", "USD"),
                    "timezone_name": row.get("timezone_name", "UTC"),
                    "account_status": row.get("account_status", 1),
                    "business_name": row.get("business_name")
                })

            paging = data.get("paging", {})
            next_url = paging.get("next")
            if next_url and len(accounts) < 500:
                # Meta returns a full URL in next, or after cursor
                cursors = paging.get("cursors", {})
                after = cursors.get("after")
                if after:
                    params["after"] = after
                else:
                    break
            else:
                break

        return accounts

    async def get_campaigns(self, ad_account_id: str) -> list[dict[str, Any]]:
        """Retrieves campaigns for an ad account with objective and status."""
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        campaigns: list[dict[str, Any]] = []
        endpoint = f"/{account_id}/campaigns"
        params = {
            "fields": "id,name,objective,status,effective_status,start_time,stop_time",
            "limit": "100"
        }

        while True:
            data = await self._make_request("GET", endpoint, params=params)
            rows = data.get("data", [])
            for row in rows:
                campaigns.append({
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "objective": row.get("objective", "OUTCOME_TRAFFIC"),
                    "status": row.get("status", "ACTIVE"),
                    "effective_status": row.get("effective_status", "ACTIVE")
                })

            paging = data.get("paging", {})
            after = paging.get("cursors", {}).get("after")
            if after and len(campaigns) < 500:
                params["after"] = after
            else:
                break

        return campaigns

    async def get_insights(
        self,
        ad_account_id: str,
        since_date: str | None = None,
        until_date: str | None = None,
        campaign_ids: list[str] | None = None,
        time_range: dict[str, str] | None = None,
        timezone_str: str = "Asia/Tashkent",
        use_account_attribution_setting: bool = DEFAULT_USE_ACCOUNT_ATTRIBUTION_SETTING
    ) -> dict[str, Any]:
        """
        Queries account-level insights filtered by campaign IDs (if specified)
        to ensure Meta returns de-duplicated reach across campaigns.
        Forces timezone synchronization with the ad account timezone for dynamic time_range construction.
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import json

        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        endpoint = f"/{account_id}/insights"

        fields = (
            "spend,impressions,clicks,inline_link_clicks,reach,frequency,"
            "actions,action_values,cost_per_action_type,purchase_roas,results,"
            "date_start,date_stop"
        )

        # Dynamic date resolution: default strictly to today in ad account timezone if dates are not provided
        if not time_range:
            if not since_date or not until_date:
                try:
                    tz = ZoneInfo(timezone_str)
                except Exception:
                    tz = ZoneInfo("Asia/Tashkent")
                today_str = datetime.now(tz).strftime("%Y-%m-%d")
                since_date = since_date or today_str
                until_date = until_date or today_str
            time_range_param = f'{{"since":"{since_date}","until":"{until_date}"}}'
        else:
            time_range_param = json.dumps(time_range) if isinstance(time_range, dict) else str(time_range)

        params: dict[str, Any] = {
            "level": "account",
            "fields": fields,
            "time_range": time_range_param
        }

        if use_account_attribution_setting:
            params["use_account_attribution_setting"] = "true"

        if campaign_ids:
            # Filter specifically by these campaign IDs
            filtering = [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]
            params["filtering"] = json.dumps(filtering)

        req_time_iso = datetime.now(timezone.utc).isoformat()
        data = await self._make_request("GET", endpoint, params=params)
        insight_rows = data.get("data", [])
        if insight_rows:
            row = insight_rows[0]
            logger.info(
                f"[MetaInsights] Query at {req_time_iso} for {account_id} ({since_date}..{until_date}): "
                f"date_start={row.get('date_start')}, date_stop={row.get('date_stop')}, spend={row.get('spend')}, "
                f"impressions={row.get('impressions')}, clicks={row.get('clicks')}"
            )
            return row
        logger.info(f"[MetaInsights] Query at {req_time_iso} for {account_id} ({since_date}..{until_date}): empty response")
        return {}

    async def get_multi_period_insights(
        self,
        ad_account_id: str,
        periods: list[tuple[str, str]],
        campaign_ids: list[str] | None = None,
        timezone_str: str = "Asia/Tashkent",
        use_account_attribution_setting: bool = DEFAULT_USE_ACCOUNT_ATTRIBUTION_SETTING
    ) -> dict[tuple[str, str], dict[str, Any] | None]:
        """
        Fetches insights for multiple time periods (e.g. current and previous) using
        a single account-level query with `time_ranges` to optimize Meta API rate limits.
        Matches returned rows by date_start/date_stop (ignoring response order).
        If a period is missing in the response, it is mapped to None.
        Falls back to separate individual requests if time_ranges fails.
        """
        import json

        result: dict[tuple[str, str], dict[str, Any] | None] = {p: None for p in periods}
        if not periods:
            return result

        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        endpoint = f"/{account_id}/insights"

        fields = (
            "spend,impressions,clicks,inline_link_clicks,reach,frequency,"
            "actions,action_values,cost_per_action_type,purchase_roas,results,"
            "date_start,date_stop"
        )

        time_ranges_payload = [{"since": p[0], "until": p[1]} for p in periods]
        params: dict[str, Any] = {
            "level": "account",
            "fields": fields,
            "time_ranges": json.dumps(time_ranges_payload)
        }
        if use_account_attribution_setting:
            params["use_account_attribution_setting"] = "true"
        if campaign_ids:
            filtering = [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]
            params["filtering"] = json.dumps(filtering)

        req_time_iso = datetime.now(timezone.utc).isoformat()
        use_fallback = False
        try:
            data = await self._make_request("GET", endpoint, params=params)
            rows = data.get("data", [])
            for r in rows:
                logger.info(
                    f"[MetaInsightsMulti] Query at {req_time_iso} for {account_id}: "
                    f"date_start={r.get('date_start')}, date_stop={r.get('date_stop')}, spend={r.get('spend')}"
                )
            for p in periods:
                s, u = p
                matched = next((r for r in rows if r.get("date_start") == s and r.get("date_stop") == u), None)
                result[p] = matched
            return result
        except MetaTokenExpiredError:
            raise
        except Exception as exc:
            logger.warning(
                f"Multi-range insights request failed for {ad_account_id} with time_ranges: {exc}. "
                "Falling back to individual period requests."
            )
            use_fallback = True

        if use_fallback:
            for p in periods:
                s, u = p
                try:
                    row = await self.get_insights(
                        ad_account_id=ad_account_id,
                        since_date=s,
                        until_date=u,
                        campaign_ids=campaign_ids,
                        timezone_str=timezone_str,
                        use_account_attribution_setting=use_account_attribution_setting
                    )
                    result[p] = row if row else None
                except MetaTokenExpiredError:
                    raise
                except Exception as exc:
                    logger.warning(f"Fallback request for period {s}..{u} failed: {exc}")
                    result[p] = None

        return result

    async def get_campaign_insights(
        self,
        ad_account_id: str,
        since_date: str,
        until_date: str,
        campaign_ids: list[str] | None = None,
        use_account_attribution_setting: bool = DEFAULT_USE_ACCOUNT_ATTRIBUTION_SETTING,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Queries campaign-level insights with pagination (handling >25 campaigns via cursor),
        filtering by spend > 0 to exclude inactive campaigns and optimize response size.
        Used for campaign-level metric extraction (e.g. total_profile_visits).
        """
        import json

        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        endpoint = f"/{account_id}/insights"

        fields = (
            "campaign_id,campaign_name,objective,spend,impressions,clicks,inline_link_clicks,"
            "reach,actions,action_values,cost_per_action_type,results"
        )
        time_range_param = f'{{"since":"{since_date}","until":"{until_date}"}}'

        filtering: list[dict[str, Any]] = [
            {"field": "spend", "operator": "GREATER_THAN", "value": "0"}
        ]
        if campaign_ids:
            filtering.append({"field": "campaign.id", "operator": "IN", "value": campaign_ids})

        params: dict[str, Any] = {
            "level": "campaign",
            "fields": fields,
            "time_range": time_range_param,
            "filtering": json.dumps(filtering),
            "limit": str(limit),
        }
        if use_account_attribution_setting:
            params["use_account_attribution_setting"] = "true"

        all_campaign_rows: list[dict[str, Any]] = []

        while True:
            data = await self._make_request("GET", endpoint, params=params)
            rows = data.get("data", [])
            all_campaign_rows.extend(rows)

            paging = data.get("paging", {})
            cursors = paging.get("cursors", {})
            after = cursors.get("after")
            next_url = paging.get("next")

            if after and next_url and len(rows) > 0 and len(all_campaign_rows) < 1000:
                params["after"] = after
            else:
                break

        return all_campaign_rows

