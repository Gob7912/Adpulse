import httpx
import asyncio
import logging
from typing import Any, Optional
from app.config import settings

logger = logging.getLogger("adpulse.meta_client")

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

                        # Code 190: Invalid or expired OAuth access token
                        if err_code == 190:
                            logger.warning(f"Meta token expired or invalid (code {err_code}, subcode {err_subcode}): {err_msg}")
                            raise MetaTokenExpiredError(
                                f"Токен Meta устарел или недействителен (код {err_code}). Пожалуйста, обновите токен.",
                                code=err_code,
                                subcode=err_subcode,
                                is_auth_error=True
                            )

                        # Code 17 / 613: Rate limit exceeded -> retry with exponential backoff
                        if err_code in (17, 613) and attempt < max_retries:
                            logger.info(f"Meta rate limit hit, backing off {delay}s (attempt {attempt}/{max_retries})")
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
        """Validates token by querying /me and retrieves user profile details."""
        data = await self._make_request("GET", "/me", params={"fields": "id,name,picture.type(large)"})
        user_id = data.get("id")
        user_name = data.get("name", "Meta System User")
        avatar_url = None
        if "picture" in data and "data" in data["picture"]:
            avatar_url = data["picture"]["data"].get("url")

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
        since_date: str,
        until_date: str,
        campaign_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Queries account-level insights filtered by campaign IDs (if specified)
        to ensure Meta returns de-duplicated reach across campaigns.
        """
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        endpoint = f"/{account_id}/insights"

        fields = (
            "spend,impressions,clicks,inline_link_clicks,reach,frequency,"
            "actions,action_values,cost_per_action_type"
        )
        params: dict[str, Any] = {
            "level": "account",
            "fields": fields,
            "time_range": f'{{"since":"{since_date}","until":"{until_date}"}}'
        }

        if campaign_ids:
            import json
            # Filter specifically by these campaign IDs
            filtering = [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]
            params["filtering"] = json.dumps(filtering)

        data = await self._make_request("GET", endpoint, params=params)
        insight_rows = data.get("data", [])
        if insight_rows:
            return insight_rows[0]
        return {}
