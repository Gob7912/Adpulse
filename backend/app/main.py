from datetime import datetime, timezone
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # Ensure all models are imported
from app.api.auth import router as auth_router
from app.api.destinations import router as destinations_router
from app.api.history import router as history_router
from app.api.meta import router as meta_router
from app.api.reports import router as reports_router
from app.config import settings
from app.database import Base, engine, get_db
from app.models.worker_heartbeat import WorkerHeartbeat

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("adpulse")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} backend service...")
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas verified.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME} backend...")
    await engine.dispose()

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Automated Meta Ads reporting SaaS engine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(destinations_router, prefix="/api")
app.include_router(history_router, prefix="/api")

@app.get("/health")
async def health_check(response: Response, db: AsyncSession = Depends(get_db)):
    now_utc = datetime.now(timezone.utc)
    worker_status = "ok"
    worker_message = "healthy"

    try:
        hb = await db.scalar(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == "scheduler_worker")
        )
        if hb is None:
            worker_status = "stale"
            worker_message = "worker stale: no heartbeat recorded"
        else:
            hb_tz = hb.last_heartbeat_at if hb.last_heartbeat_at.tzinfo else hb.last_heartbeat_at.replace(tzinfo=timezone.utc)
            age_seconds = (now_utc - hb_tz).total_seconds()
            if age_seconds > 120:  # older than 2 minutes
                worker_status = "stale"
                worker_message = f"worker stale: last seen {int(age_seconds)}s ago"
            else:
                worker_message = f"heartbeat {int(age_seconds)}s ago"
    except Exception as e:
        logger.warning(f"Health check failed querying worker heartbeat: {e}")
        worker_status = "unknown"
        worker_message = str(e)

    overall_status = "ok" if worker_status == "ok" else "degraded"
    if worker_status == "stale":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "worker": {
            "status": worker_status,
            "message": worker_message
        },
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }
