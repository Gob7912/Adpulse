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


@pytest.mark.asyncio
async def test_report_editing_edge_cases(client: AsyncClient, test_db_session):
    from sqlalchemy import update

    from app.models.destination import Destination

    # Register Owner
    reg = await client.post("/api/auth/register", json={"email": "owner@example.com", "password": "password123"})
    token_owner = reg.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    # Register Other User
    reg_other = await client.post("/api/auth/register", json={"email": "other@example.com", "password": "password123"})
    token_other = reg_other.json()["access_token"]
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # Create initial report
    create_res = await client.post(
        "/api/reports",
        json={
            "name": "Original Report",
            "meta_account_id": "act_111",
            "meta_account_name": "Account 1",
            "periodicity": "daily",
            "schedule_time": "08:00",
            "send_timezone": "Asia/Tashkent",
            "campaign_scope_type": "specific",
            "specific_campaign_ids": ["camp_1", "camp_2"],
            "delivery_channels": ["telegram"]
        },
        headers=headers_owner
    )
    assert create_res.status_code == 201
    rep = create_res.json()
    rep_id = rep["id"]
    orig_next_run = rep["next_run_at"]
    orig_tg_dest = next(d for d in rep["destinations"] if d["destination_type"] == "telegram")
    orig_code = orig_tg_dest["one_time_code"]

    # Simulating telegram connected state in DB
    await test_db_session.execute(
        update(Destination)
        .where(Destination.id == orig_tg_dest["id"])
        .values(telegram_chat_id=12345678, telegram_thread_id=42, is_connected=True, telegram_chat_title="My Group")
    )
    await test_db_session.commit()

    # Case a: Paused report stays paused after editing
    pause_res = await client.post(f"/api/reports/{rep_id}/pause", headers=headers_owner)
    assert pause_res.status_code == 200
    assert pause_res.json()["is_active"] is False

    edit_res = await client.put(
        f"/api/reports/{rep_id}",
        json={"name": "Still Paused Report"},
        headers=headers_owner
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["name"] == "Still Paused Report"
    assert edit_res.json()["is_active"] is False  # (Case a: stays paused)

    # Case b: Telegram connection preserved (chat_id, thread_id, one_time_code not reset)
    edit_tg = await client.put(
        f"/api/reports/{rep_id}",
        json={"delivery_channels": ["telegram"]},
        headers=headers_owner
    )
    assert edit_tg.status_code == 200
    tg_dest_after = next(d for d in edit_tg.json()["destinations"] if d["destination_type"] == "telegram")
    assert tg_dest_after["one_time_code"] == orig_code
    assert tg_dest_after["telegram_chat_id"] == 12345678
    assert tg_dest_after["telegram_thread_id"] == 42
    assert tg_dest_after["is_connected"] is True  # (Case b: connection preserved)

    # Case c: next_run_at without schedule change stays unchanged; with schedule change is recalculated
    edit_name_only = await client.put(
        f"/api/reports/{rep_id}",
        json={"name": "Only Name Changed"},
        headers=headers_owner
    )
    assert edit_name_only.status_code == 200
    assert edit_name_only.json()["next_run_at"] == orig_next_run  # (Case c1: unchanged schedule preserves next_run_at)

    edit_sched = await client.put(
        f"/api/reports/{rep_id}",
        json={"schedule_time": "15:00"},
        headers=headers_owner
    )
    assert edit_sched.status_code == 200
    assert edit_sched.json()["next_run_at"] != orig_next_run  # (Case c2: changed schedule recalculates next_run_at)

    # Case d & Point 2: Changing ad account updates currency, account_timezone, and recalculates next_run_at
    prev_next_run = edit_sched.json()["next_run_at"]
    edit_acc = await client.put(
        f"/api/reports/{rep_id}",
        json={
            "meta_account_id": "act_222",
            "meta_account_name": "Account 2",
            "currency": "EUR",
            "account_timezone": "America/Los_Angeles"
        },
        headers=headers_owner
    )
    assert edit_acc.status_code == 200
    assert edit_acc.json()["meta_account_id"] == "act_222"
    assert edit_acc.json()["currency"] == "EUR"  # Currency updated from new account
    assert edit_acc.json()["account_timezone"] == "America/Los_Angeles"  # Timezone updated from new account
    assert edit_acc.json()["specific_campaign_ids"] == []  # (Case d: campaigns from old account reset)
    assert edit_acc.json()["next_run_at"] != prev_next_run  # next_run_at recalculated for new timezone

    # Point 3: Remove Telegram, save, then add back
    # 1. User removes Telegram from delivery channels
    rem_tg = await client.put(
        f"/api/reports/{rep_id}",
        json={"delivery_channels": ["google_sheets"], "sheets_url": "https://docs.google.com/spreadsheets/d/abc123/edit"},
        headers=headers_owner
    )
    assert rem_tg.status_code == 200
    tg_disabled = next(d for d in rem_tg.json()["destinations"] if d["destination_type"] == "telegram")
    assert tg_disabled["is_enabled"] is False

    # 2. User adds Telegram back -> without duplicate Destination, chat_id & thread_id restored
    add_tg = await client.put(
        f"/api/reports/{rep_id}",
        json={"delivery_channels": ["telegram", "google_sheets"]},
        headers=headers_owner
    )
    assert add_tg.status_code == 200
    tg_dests_after = [d for d in add_tg.json()["destinations"] if d["destination_type"] == "telegram"]
    assert len(tg_dests_after) == 1  # No duplicate rows
    assert tg_dests_after[0]["is_enabled"] is True
    assert tg_dests_after[0]["telegram_chat_id"] == 12345678  # chat_id restored
    assert tg_dests_after[0]["telegram_thread_id"] == 42  # thread_id restored
    assert tg_dests_after[0]["is_connected"] is True
    assert tg_dests_after[0]["one_time_code"] == orig_code

    # 3. Optional user action to unlink / reset code generates new code
    reset_tg = await client.put(
        f"/api/reports/{rep_id}",
        json={"reset_telegram_code": True},
        headers=headers_owner
    )
    assert reset_tg.status_code == 200
    tg_reset = next(d for d in reset_tg.json()["destinations"] if d["destination_type"] == "telegram")
    assert tg_reset["telegram_chat_id"] is None
    assert tg_reset["is_connected"] is False
    assert tg_reset["one_time_code"] != orig_code

    # Case f: Editing another user's report returns 404
    edit_other = await client.put(
        f"/api/reports/{rep_id}",
        json={"name": "Hacked by User B"},
        headers=headers_other
    )
    assert edit_other.status_code == 404  # (Case f: 404 for non-owner)


