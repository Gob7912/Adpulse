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
