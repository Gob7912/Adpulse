import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # Ensure all models are imported
from app.api.auth import router as auth_router
from app.api.meta import router as meta_router
from app.api.reports import router as reports_router
from app.api.destinations import router as destinations_router
from app.api.history import router as history_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
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
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }
