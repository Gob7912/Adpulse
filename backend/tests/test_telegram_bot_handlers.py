from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.destination import Destination
from app.models.report import Report
from app.models.user import User
from app.services.telegram_bot import handle_link_group, handle_start


@pytest.mark.asyncio
async def test_telegram_bot_handle_start_personal(test_db_session):
    # Setup test user and report
    user = User(email="tgtest@example.com", hashed_password="hashed_test_password")
    test_db_session.add(user)
    await test_db_session.flush()

    report = Report(
        user_id=user.id,
        name="TG Report",
        meta_account_id="act_111",
        meta_account_name="Account 1",
        currency="USD",
        account_timezone="UTC",
        periodicity="daily",
        schedule_time="08:00",
        send_timezone="UTC"
    )
    test_db_session.add(report)
    await test_db_session.flush()

    dest = Destination(
        report_id=report.id,
        destination_type="telegram",
        is_enabled=True,
        telegram_target_type="personal",
        one_time_code="valid_code_12345",
        is_connected=False
    )
    test_db_session.add(dest)
    await test_db_session.commit()

    # Mock Message
    mock_msg = MagicMock()
    mock_msg.text = "/start valid_code_12345"
    mock_msg.chat.type = "private"
    mock_msg.chat.id = 999888
    mock_msg.from_user.full_name = "Alex Developer"
    mock_msg.from_user.username = "alexdev"
    mock_msg.answer = AsyncMock()

    # Patch AsyncSessionLocal in telegram_bot to return a session on our test db
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=test_db_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.telegram_bot.AsyncSessionLocal", return_value=session_cm):
        await handle_start(mock_msg)

    # Check answer called with success
    mock_msg.answer.assert_called_once()
    assert "успешно подключен" in mock_msg.answer.call_args[0][0]

    # Verify dest is connected in DB
    await test_db_session.refresh(dest)
    assert dest.is_connected is True
    assert dest.telegram_chat_id == 999888
    assert dest.telegram_target_type == "personal"

@pytest.mark.asyncio
async def test_telegram_bot_handle_link_group_with_topic(test_db_session):
    # Setup test user and report
    user = User(email="grouptest@example.com", hashed_password="hashed_test_password")
    test_db_session.add(user)
    await test_db_session.flush()

    report = Report(
        user_id=user.id,
        name="Team Report",
        meta_account_id="act_222",
        meta_account_name="Account 2",
        currency="USD",
        account_timezone="UTC",
        periodicity="daily",
        schedule_time="08:00",
        send_timezone="UTC"
    )
    test_db_session.add(report)
    await test_db_session.flush()

    dest = Destination(
        report_id=report.id,
        destination_type="telegram",
        is_enabled=True,
        telegram_target_type="personal",
        one_time_code="group_code_67890",
        is_connected=False
    )
    test_db_session.add(dest)
    await test_db_session.commit()

    # Mock Message in supergroup with topic
    mock_msg = MagicMock()
    mock_msg.text = "/link group_code_67890"
    mock_msg.chat.type = "supergroup"
    mock_msg.chat.id = -10099887766
    mock_msg.chat.title = "Marketing Team Chat"
    mock_msg.message_thread_id = 42
    mock_msg.answer = AsyncMock()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=test_db_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.telegram_bot.AsyncSessionLocal", return_value=session_cm):
        await handle_link_group(mock_msg)

    # Check answer called with success
    mock_msg.answer.assert_called_once()
    assert "Группа успешно привязана" in mock_msg.answer.call_args[0][0]
    assert "#42" in mock_msg.answer.call_args[0][0]

    # Verify in DB
    await test_db_session.refresh(dest)
    assert dest.is_connected is True
    assert dest.telegram_chat_id == -10099887766
    assert dest.telegram_thread_id == 42
    assert dest.telegram_target_type == "group_channel"
