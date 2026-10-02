from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.telegram_sender import TelegramSender


@pytest.mark.asyncio
async def test_telegram_sender_with_thread_id():
    sender = TelegramSender(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    sender.bot = MagicMock()
    sender.bot.send_message = AsyncMock(return_value=True)

    success = await sender.send_message(
        chat_id=-100123456789,
        text="<b>Test Message</b>",
        message_thread_id=42
    )

    assert success is True
    sender.bot.send_message.assert_called_once_with(
        chat_id=-100123456789,
        text="<b>Test Message</b>",
        message_thread_id=42
    )

@pytest.mark.asyncio
async def test_telegram_sender_token_expired_alert():
    sender = TelegramSender(bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    sender.bot = MagicMock()
    sender.bot.send_message = AsyncMock(return_value=True)

    await sender.send_token_expired_alert(
        chat_id=12345,
        report_name="Клиент Alpha",
        message_thread_id=None
    )

    sender.bot.send_message.assert_called_once()
    call_args = sender.bot.send_message.call_args[1]
    assert call_args["chat_id"] == 12345
    assert "Клиент Alpha" in call_args["text"]
    assert "Error 190" in call_args["text"]
