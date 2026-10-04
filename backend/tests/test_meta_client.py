from unittest.mock import AsyncMock, patch

import pytest

from app.services.meta_client import MetaClient, MetaTokenExpiredError


@pytest.mark.asyncio
async def test_meta_client_verify_token_success():
    client = MetaClient(access_token="valid_test_token_123")
    mock_response = {
        "id": "10001",
        "name": "Muhammadsoadiq Muxtarov",
        "picture": {
            "data": {"url": "https://graph.facebook.com/10001/picture"}
        }
    }

    with patch.object(client, "_make_request", new=AsyncMock(return_value=mock_response)):
        res = await client.verify_token()
        assert res["meta_user_id"] == "10001"
        assert res["meta_user_name"] == "Muhammadsoadiq Muxtarov"
        assert "picture" in res["meta_avatar_url"]

@pytest.mark.asyncio
async def test_meta_client_token_expired_error():
    client = MetaClient(access_token="expired_token")

    async def mock_expired(*args, **kwargs):
        raise MetaTokenExpiredError("Токен Meta устарел или недействителен (код 190).", code=190)

    with patch.object(client, "_make_request", side_effect=mock_expired):
        with pytest.raises(MetaTokenExpiredError) as exc_info:
            await client.get_ad_accounts()
        assert exc_info.value.code == 190

@pytest.mark.asyncio
async def test_meta_client_get_ad_accounts_pagination():
    client = MetaClient(access_token="test_token")
    mock_page1 = {
        "data": [
            {"id": "act_101", "account_id": "101", "name": "Account 1", "currency": "USD", "timezone_name": "Asia/Tashkent"}
        ],
        "paging": {
            "cursors": {"after": "cursor_next_page"},
            "next": "https://graph.facebook.com/v21.0/me/adaccounts?after=cursor_next_page"
        }
    }
    mock_page2 = {
        "data": [
            {"id": "act_102", "account_id": "102", "name": "Account 2", "currency": "EUR", "timezone_name": "UTC"}
        ],
        "paging": {}
    }

    calls = [mock_page1, mock_page2]

    async def mock_make_request(*args, **kwargs):
        return calls.pop(0)

    with patch.object(client, "_make_request", side_effect=mock_make_request):
        accounts = await client.get_ad_accounts()
        assert len(accounts) == 2
        assert accounts[0]["id"] == "act_101"
        assert accounts[1]["id"] == "act_102"


@pytest.mark.asyncio
async def test_meta_client_get_insights_tashkent_dynamic_range():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    client = MetaClient(access_token="test_token")
    mock_resp = {"data": [{"spend": "14.57", "impressions": "5200"}]}

    recorded_params = {}

    async def mock_req(method, endpoint, params=None, max_retries=3):
        nonlocal recorded_params
        recorded_params = params
        return mock_resp

    with patch.object(client, "_make_request", side_effect=mock_req):
        # Call without explicit dates -> defaults to today in Asia/Tashkent
        res = await client.get_insights("act_12345")
        assert res["spend"] == "14.57"
        today_tashkent = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d")
        assert f'"since":"{today_tashkent}"' in recorded_params["time_range"]
        assert f'"until":"{today_tashkent}"' in recorded_params["time_range"]
        assert recorded_params.get("use_account_attribution_setting") == "true"


@pytest.mark.asyncio
async def test_meta_client_attribution_setting_toggle():
    client = MetaClient(access_token="test_token")
    mock_resp = {"data": [{"spend": "10.00"}]}

    recorded_params = {}

    async def mock_req(method, endpoint, params=None, max_retries=3):
        nonlocal recorded_params
        recorded_params = params
        return mock_resp

    with patch.object(client, "_make_request", side_effect=mock_req):
        await client.get_insights("act_12345", use_account_attribution_setting=False)
        assert "use_account_attribution_setting" not in recorded_params

        await client.get_insights("act_12345", use_account_attribution_setting=True)
        assert recorded_params["use_account_attribution_setting"] == "true"


def test_is_meta_rate_limit():
    from app.services.meta_client import is_meta_rate_limit
    assert is_meta_rate_limit(4) is True
    assert is_meta_rate_limit(17) is True
    assert is_meta_rate_limit(32) is True
    assert is_meta_rate_limit(613) is True
    assert is_meta_rate_limit(80000) is True
    assert is_meta_rate_limit(80004) is True
    assert is_meta_rate_limit(80014) is True
    assert is_meta_rate_limit(80099) is True
    # Non rate-limit codes
    assert is_meta_rate_limit(190) is False
    assert is_meta_rate_limit(200) is False
    assert is_meta_rate_limit(10) is False
    # Transient flag
    assert is_meta_rate_limit(500, is_transient=True) is True


@pytest.mark.asyncio
async def test_get_multi_period_insights_reordered():
    client = MetaClient(access_token="test_token")
    periods = [("2026-10-02", "2026-10-02"), ("2026-10-03", "2026-10-03")]

    # Meta returns rows in REVERSE order (Oct 3 first, Oct 2 second)
    mock_resp = {
        "data": [
            {"date_start": "2026-10-03", "date_stop": "2026-10-03", "spend": "14.57"},
            {"date_start": "2026-10-02", "date_stop": "2026-10-02", "spend": "46.45"},
        ]
    }

    with patch.object(client, "_make_request", return_value=mock_resp):
        res = await client.get_multi_period_insights("act_12345", periods)
        assert res[("2026-10-03", "2026-10-03")]["spend"] == "14.57"
        assert res[("2026-10-02", "2026-10-02")]["spend"] == "46.45"


@pytest.mark.asyncio
async def test_get_multi_period_insights_missing_row():
    client = MetaClient(access_token="test_token")
    periods = [("2026-10-02", "2026-10-02"), ("2026-10-03", "2026-10-03")]

    # Meta returns only Oct 3 row (no spend on Oct 2)
    mock_resp = {
        "data": [
            {"date_start": "2026-10-03", "date_stop": "2026-10-03", "spend": "14.57"},
        ]
    }

    with patch.object(client, "_make_request", return_value=mock_resp):
        res = await client.get_multi_period_insights("act_12345", periods)
        assert res[("2026-10-03", "2026-10-03")]["spend"] == "14.57"
        assert res[("2026-10-02", "2026-10-02")] is None


@pytest.mark.asyncio
async def test_get_multi_period_insights_fallback_on_error():
    client = MetaClient(access_token="test_token")
    periods = [("2026-10-02", "2026-10-02"), ("2026-10-03", "2026-10-03")]

    # First call with time_ranges fails with an API error
    # Subsequent calls with time_range succeed individually
    call_count = 0

    async def mock_req(method, endpoint, params=None, max_retries=3):
        nonlocal call_count
        call_count += 1
        if "time_ranges" in params:
            raise MetaAPIError("Unsupported time_ranges param")
        if "2026-10-02" in str(params.get("time_range")):
            return {"data": [{"date_start": "2026-10-02", "date_stop": "2026-10-02", "spend": "46.45"}]}
        if "2026-10-03" in str(params.get("time_range")):
            return {"data": [{"date_start": "2026-10-03", "date_stop": "2026-10-03", "spend": "14.57"}]}
        return {"data": []}

    with patch.object(client, "_make_request", side_effect=mock_req):
        res = await client.get_multi_period_insights("act_12345", periods)
        assert res[("2026-10-03", "2026-10-03")]["spend"] == "14.57"
        assert res[("2026-10-02", "2026-10-02")]["spend"] == "46.45"
        # 1 failed time_ranges call + 2 fallback individual calls = 3 calls
        assert call_count == 3


@pytest.mark.asyncio
async def test_get_campaign_insights_pagination_over_25():
    """
    Verifies that get_campaign_insights handles cursor pagination when there are
    more than 25 campaigns (e.g. 30 campaigns across 2 pages), properly following
    paging.cursors.after and filtering by spend > 0.
    """
    import json
    client = MetaClient(access_token="test_token")

    page_1_data = [{"campaign_id": f"camp_{i}", "campaign_name": f"Campaign {i}", "spend": "10.0"} for i in range(1, 26)]
    page_2_data = [{"campaign_id": f"camp_{i}", "campaign_name": f"Campaign {i}", "spend": "5.0"} for i in range(26, 31)]

    calls_params = []

    async def mock_req(method, endpoint, params=None, max_retries=3):
        calls_params.append(dict(params or {}))
        if len(calls_params) == 1:
            return {
                "data": page_1_data,
                "paging": {
                    "cursors": {"after": "cursor_page_2"},
                    "next": "https://graph.facebook.com/v21.0/act_123/insights?after=cursor_page_2"
                }
            }
        else:
            return {
                "data": page_2_data,
                "paging": {}
            }

    with patch.object(client, "_make_request", side_effect=mock_req):
        camps = await client.get_campaign_insights(
            ad_account_id="act_123",
            since_date="2026-10-03",
            until_date="2026-10-03",
            limit=25
        )

        assert len(camps) == 30
        assert camps[0]["campaign_id"] == "camp_1"
        assert camps[29]["campaign_id"] == "camp_30"

        # Check call 1 had level=campaign, limit=25, and spend > 0 filter
        assert calls_params[0]["level"] == "campaign"
        assert calls_params[0]["limit"] == "25"
        filtering_1 = json.loads(calls_params[0]["filtering"])
        assert {"field": "spend", "operator": "GREATER_THAN", "value": "0"} in filtering_1
        assert "after" not in calls_params[0]

        # Check call 2 requested after=cursor_page_2
        assert calls_params[1]["after"] == "cursor_page_2"

