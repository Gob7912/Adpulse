import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.destination import Destination
from app.services.telegram_links import clean_and_validate_start_code

logger = logging.getLogger("adpulse.telegram_bot")

dp = Dispatcher()

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    # Check for deep linking payload: /start <code_here>
    args = message.text.split(maxsplit=1)
    raw_code = args[1].strip() if len(args) > 1 else None

    if not raw_code:
        await message.answer(
            "👋 <b>Привет! Это бот системы AdPulse.</b>\n\n"
            "Я автоматически доставляю отчёты по рекламе Meta (Facebook / Instagram).\n"
            "Чтобы привязать этот чат к вашему отчёту, используйте кнопку в мастере создания отчёта в AdPulse.",
            parse_mode=ParseMode.HTML
        )
        return

    code, code_err = clean_and_validate_start_code(raw_code)
    if not code:
        await message.answer(
            f"❌ <b>Некорректный код привязки:</b> {code_err or 'код повреждён'}.",
            parse_mode=ParseMode.HTML
        )
        return

    # Check whether message is sent in private or in a group (startgroup deep-link)
    is_group_chat = message.chat.type in ('group', 'supergroup')

    # Look up destination with this one_time_code
    async with AsyncSessionLocal() as session:
        query = (
            select(Destination)
            .options(selectinload(Destination.report))
            .where(Destination.one_time_code == code)
        )
        result = await session.execute(query)
        dest = result.scalars().first()

        if not dest:
            await message.answer(
                "❌ <b>Код привязки не найден или устарел.</b>\n"
                "Пожалуйста, вернитесь в личный кабинет AdPulse и скопируйте новую ссылку.",
                parse_mode=ParseMode.HTML
            )
            return

        report_id = dest.report_id
        thread_id = getattr(message, "message_thread_id", None)

        if is_group_chat:
            # Group / Channel connection via startgroup
            target_dest = dest
            if dest.is_connected and dest.telegram_target_type == "personal":
                # Find or create a group destination for the same report so both can exist
                existing_grp_q = select(Destination).where(
                    Destination.report_id == report_id,
                    Destination.destination_type == "telegram",
                    Destination.telegram_target_type == "group_channel"
                )
                grp_res = await session.execute(existing_grp_q)
                target_dest = grp_res.scalars().first()
                if not target_dest:
                    target_dest = Destination(
                        report_id=report_id,
                        destination_type="telegram",
                        is_enabled=True,
                        one_time_code=code
                    )
                    session.add(target_dest)

            target_dest.telegram_chat_id = message.chat.id
            target_dest.telegram_thread_id = thread_id
            target_dest.telegram_chat_title = message.chat.title or "Group"
            target_dest.telegram_target_type = "group_channel"
            target_dest.is_connected = True
            await session.commit()

            topic_note = f" (в тему #{thread_id})" if thread_id else ""
            report_name = dest.report.name if dest.report else "ваш отчёт"
            await message.answer(
                f"✅ <b>Группа успешно привязана к AdPulse!</b>\n\n"
                f"Отчёт: <b>«{report_name}»</b>\n"
                f"Чат: <b>{message.chat.title}</b>{topic_note}\n\n"
                f"Сводка рекламы будет приходить сюда автоматически по расписанию.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Connected group destination {target_dest.id} via /start in chat {message.chat.id}, thread {thread_id}")

        else:
            # Personal private chat
            target_dest = dest
            if dest.is_connected and dest.telegram_target_type == "group_channel":
                # Report is already bound to a group; bind personal without overwriting group
                existing_pers_q = select(Destination).where(
                    Destination.report_id == report_id,
                    Destination.destination_type == "telegram",
                    Destination.telegram_target_type == "personal"
                )
                pers_res = await session.execute(existing_pers_q)
                target_dest = pers_res.scalars().first()
                if not target_dest:
                    target_dest = Destination(
                        report_id=report_id,
                        destination_type="telegram",
                        is_enabled=True,
                        one_time_code=code
                    )
                    session.add(target_dest)

            target_dest.telegram_chat_id = message.chat.id
            target_dest.telegram_chat_title = message.from_user.full_name or message.from_user.username or "Personal"
            target_dest.telegram_target_type = "personal"
            target_dest.telegram_thread_id = None
            target_dest.is_connected = True
            await session.commit()

            report_name = dest.report.name if dest.report else "ваш отчёт"
            await message.answer(
                f"✅ <b>Telegram успешно подключен!</b>\n\n"
                f"Личный чат привязан к отчёту: <b>«{report_name}»</b>.\n"
                f"Сводка по рекламе будет приходить сюда автоматически по настроенному расписанию.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Connected personal Telegram destination {target_dest.id} for user {message.chat.id}")

@dp.message(Command("link"))
async def handle_link_group(message: types.Message):
    # Usage in groups: /link <one_time_code>
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "⚠️ <b>Укажите код привязки.</b>\n"
            "Формат: <code>/link &lt;код_из_мастера_adpulse&gt;</code>",
            parse_mode=ParseMode.HTML
        )
        return

    code, code_err = clean_and_validate_start_code(parts[1])
    if not code:
        await message.answer(
            f"❌ <b>Некорректный код привязки:</b> {code_err or 'код повреждён'}.",
            parse_mode=ParseMode.HTML
        )
        return

    async with AsyncSessionLocal() as session:
        query = (
            select(Destination)
            .options(selectinload(Destination.report))
            .where(Destination.one_time_code == code)
        )
        result = await session.execute(query)
        dest = result.scalars().first()

        if not dest:
            await message.answer(
                "❌ <b>Код привязки не найден или недействителен.</b>\n"
                "Проверьте код в интерфейсе AdPulse.",
                parse_mode=ParseMode.HTML
            )
            return

        report_id = dest.report_id
        thread_id = getattr(message, "message_thread_id", None)

        target_dest = dest
        # If destination was already linked as personal, keep it and create/update group destination
        if dest.is_connected and dest.telegram_target_type == "personal":
            existing_grp_q = select(Destination).where(
                Destination.report_id == report_id,
                Destination.destination_type == "telegram",
                Destination.telegram_target_type == "group_channel"
            )
            grp_res = await session.execute(existing_grp_q)
            target_dest = grp_res.scalars().first()
            if not target_dest:
                target_dest = Destination(
                    report_id=report_id,
                    destination_type="telegram",
                    is_enabled=True,
                    one_time_code=code
                )
                session.add(target_dest)

        target_dest.telegram_chat_id = message.chat.id
        target_dest.telegram_thread_id = thread_id
        target_dest.telegram_chat_title = message.chat.title or "Group"
        target_dest.telegram_target_type = "group_channel"
        target_dest.is_connected = True
        await session.commit()

        topic_note = f" (в тему #{thread_id})" if thread_id else ""
        report_name = dest.report.name if dest.report else "ваш отчёт"

        await message.answer(
            f"✅ <b>Группа успешно привязана к AdPulse!</b>\n\n"
            f"Отчёт: <b>«{report_name}»</b>\n"
            f"Чат: <b>{message.chat.title}</b>{topic_note}\n\n"
            f"Бот будет присылать утренние отчёты прямо в эту переписку.",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Connected group destination {target_dest.id} via /link in chat {message.chat.id}, thread {thread_id}")

async def run_bot_polling():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not provided. Bot polling skipped.")
        return

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logger.info("Starting Telegram bot in long polling mode...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
