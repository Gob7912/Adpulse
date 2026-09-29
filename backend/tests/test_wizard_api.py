import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_wizard_and_user_isolation(client: AsyncClient):
    # 1. Register User A
    reg_res_a = await client.post(
        "/api/auth/register",
        json={"email": "usera@example.com", "password": "password123"}
    )
    assert reg_res_a.status_code == 200
    token_a = reg_res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    reg_res_b = await client.post(
        "/api/auth/register",
        json={"email": "userb@example.com", "password": "password123"}
    )
    assert reg_res_b.status_code == 200
    token_b = reg_res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Check metadata endpoint
    meta_res = await client.get("/api/meta/metadata")
    assert meta_res.status_code == 200
    meta_data = meta_res.json()
    assert len(meta_data["metrics"]) >= 20
    assert len(meta_data["templates"]) == 4

    # 4. Live Preview check (Step 3)
    prev_res = await client.post(
        "/api/reports/live-preview",
        json={
            "metrics": ["spend", "impressions", "cpm"],
            "metric_labels": {"spend": "Потрачено"},
            "lang": "ru",
            "currency": "USD"
        }
    )
    assert prev_res.status_code == 200
    assert "Потрачено" in prev_res.json()["formatted_text"]

    # 5. User A creates a Report (Step 4 & 5)
    report_payload = {
        "name": "Клиент Alpha - Ежедневно",
        "meta_account_id": "act_123456789",
        "meta_account_name": "Alpha Store",
        "currency": "USD",
        "account_timezone": "Asia/Tashkent",
        "campaign_scope_type": "filtered",
        "campaign_filter_goals": ["MESSAGES"],
        "campaign_filter_name": "PROMO",
        "metrics": ["spend", "impressions", "messages", "cost_per_dm"],
        "smart_metric_detection": True,
        "metric_labels": {"spend": "Бюджет"},
        "metric_lang": "ru",
        "periodicity": "daily",
        "schedule_time": "08:00",
        "send_timezone": "Asia/Tashkent",
        "delivery_channels": ["telegram", "google_sheets"],
        "sheets_url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
        "sheets_tab_name": "DailyReports"
    }

    create_res = await client.post("/api/reports", json=report_payload, headers=headers_a)
    assert create_res.status_code == 201
    created_report = create_res.json()
    report_id = created_report["id"]
    assert created_report["name"] == "Клиент Alpha - Ежедневно"
    assert len(created_report["destinations"]) == 2

    # Check that telegram destination has one_time_code and deep link
    tg_dest = next(d for d in created_report["destinations"] if d["destination_type"] == "telegram")
    assert tg_dest["one_time_code"] is not None
    assert "start=" in tg_dest["deep_link_personal"]

    # 6. Verify User B CANNOT view or modify User A's report (User Scoping)
    get_res_b = await client.get(f"/api/reports/{report_id}", headers=headers_b)
    assert get_res_b.status_code == 404

    # User B lists reports -> gets empty list
    list_b = await client.get("/api/reports", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0

    # User A lists reports -> sees the report
    list_a = await client.get("/api/reports", headers=headers_a)
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1

    # 7. Pause and Resume report
    pause_res = await client.post(f"/api/reports/{report_id}/pause", headers=headers_a)
    assert pause_res.status_code == 200
    assert pause_res.json()["is_active"] is False

    resume_res = await client.post(f"/api/reports/{report_id}/resume", headers=headers_a)
    assert resume_res.status_code == 200
    assert resume_res.json()["is_active"] is True

    # 8. Duplicate report
    dup_res = await client.post(f"/api/reports/{report_id}/duplicate", headers=headers_a)
    assert dup_res.status_code == 200
    assert "Копия" in dup_res.json()["name"]

    # 9. Test Bot Info endpoint
    bot_info_res = await client.get("/api/destinations/telegram/bot-info", headers=headers_a)
    assert bot_info_res.status_code == 200
    info_json = bot_info_res.json()
    assert "bot_username" in info_json
    assert "is_configured" in info_json

    # 10. Update report (Step 4 & 5 edit mode)
    update_res = await client.put(
        f"/api/reports/{report_id}",
        json={
            "name": "Клиент Alpha - Обновлен",
            "periodicity": "weekly",
            "schedule_time": "10:00",
            "schedule_weekday": 2,
            "sheets_tab_name": "NewTab"
        },
        headers=headers_a
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Клиент Alpha - Обновлен"
    assert update_res.json()["periodicity"] == "weekly"

    # 11. Delete report
    del_res = await client.delete(f"/api/reports/{report_id}", headers=headers_a)
    assert del_res.status_code == 200

