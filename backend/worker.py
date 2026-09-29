import asyncio
import logging
from app.config import settings
from app.database import engine, Base
import app.models
from app.services.scheduler_service import scheduler_service
from app.services.telegram_bot import run_bot_polling

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("adpulse.worker")

async def main():
    logger.info(f"Starting {settings.APP_NAME} background worker and Telegram bot...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Launch background tasks concurrently:
    # 1. Scheduler worker loop
    # 2. Telegram Bot long-polling
    worker_task = asyncio.create_task(scheduler_service.run_worker_loop())
    telegram_task = asyncio.create_task(run_bot_polling())

    logger.info("Worker and Telegram tasks launched successfully.")
    await asyncio.gather(worker_task, telegram_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process terminated gracefully.")
