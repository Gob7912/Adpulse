import logging
from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from app.config import settings
from app.services.telegram_links import (
    clean_and_validate_bot_username,
)

logger = logging.getLogger("adpulse.telegram_sender")

class TelegramSender:
    def __init__(self, bot_token: str | None = None):
        self.bot_token = (bot_token or settings.TELEGRAM_BOT_TOKEN or "").strip()
        self.bot = (
            Bot(
                token=self.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            if self.bot_token
            else None
        )
        self._cached_bot_username: str | None = None
        self._cache_initialized: bool = False

    def reset_cache(self):
        """Resets cached bot username (useful for tests or token rotation)."""
        self._cached_bot_username = None
        self._cache_initialized = False

    async def get_runtime_bot_username(self) -> tuple[str | None, str | None]:
        """
        Gets the bot username at runtime from Telegram getMe (and caches it).
        Returns (cleaned_username, error_message).
        """
        if self._cache_initialized and self._cached_bot_username:
            return self._cached_bot_username, None

        # 1. Try getMe if bot instance exists
        if self.bot:
            try:
                me = await self.bot.get_me()
                if me and me.username:
                    cleaned, err = clean_and_validate_bot_username(me.username)
                    if cleaned:
                        self._cached_bot_username = cleaned
                        self._cache_initialized = True
                        logger.info(f"Loaded and cached runtime bot username: @{cleaned}")
                        return self._cached_bot_username, None
                    else:
                        logger.warning(f"Telegram getMe returned invalid username format: {me.username}")
            except Exception as exc:
                logger.warning(f"Could not fetch bot username via Telegram getMe: {exc}")

        # 2. Fallback to settings.TELEGRAM_BOT_USERNAME
        fallback, err = clean_and_validate_bot_username(settings.TELEGRAM_BOT_USERNAME)
        if fallback:
            self._cached_bot_username = fallback
            self._cache_initialized = True
            return self._cached_bot_username, None

        self._cache_initialized = True
        return None, "Токен Telegram-бота не задан или бот недоступен через getMe."

    async def send_message(
        self,
        chat_id: int,
        text: str,
        message_thread_id: int | None = None
    ) -> Any:
        """Sends an HTML formatted message to a Telegram chat, optionally within a forum topic."""
        if not self.bot:
            logger.warning("Telegram bot token is not configured. Skipping message delivery.")
            return False

        try:
            sent_msg = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                message_thread_id=message_thread_id
            )
            msg_id = getattr(sent_msg, "message_id", None)
            logger.info(f"Telegram message sent to chat_id={chat_id}, thread_id={message_thread_id}, msg_id={msg_id}")
            return sent_msg
        except TelegramAPIError as exc:
            logger.error(f"Failed to send Telegram message to {chat_id}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error sending Telegram message: {exc}")
            raise

    async def send_token_expired_alert(
        self,
        chat_id: int,
        report_name: str,
        message_thread_id: int | None = None
    ) -> bool:
        """Alerts the Telegram recipient that their Meta token is expired/invalid."""
        alert_text = (
            f"⚠️ <b>Внимание: ошибка авторизации Meta Ads</b>\n\n"
            f"Токен доступа к рекламному кабинету для отчёта <b>«{report_name}»</b> "
            f"устарел или был отозван Meta (Error 190).\n\n"
            f"Автоматическая отправка отчётов приостановлена. "
            f"Пожалуйста, перейдите в панель управления AdPulse и обновите системный токен."
        )
        return await self.send_message(chat_id, alert_text, message_thread_id)

    async def close(self):
        if self.bot and self.bot.session:
            await self.bot.session.close()

telegram_sender = TelegramSender()
