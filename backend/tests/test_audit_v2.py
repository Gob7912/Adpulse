import os
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.config import Settings, settings
from app.models.admin_alert import AdminAlert
from app.models.worker_heartbeat import WorkerHeartbeat
from app.services.scheduler_service import SchedulerService

# Strictly enforce testing ONLY against adpulse_test database
PG_TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adpulse:adpulse_secure_password_replace_me@127.0.0.1:5432/adpulse_test"
    )
)
if "@db:5432" in PG_TEST_URL:
    PG_TEST_URL = PG_TEST_URL.replace("@db:5432", "@127.0.0.1:5432")
if "adpulse_test" not in PG_TEST_URL:
    PG_TEST_URL = PG_TEST_URL.rsplit("/", 1)[0] + "/adpulse_test"

pg_test_engine = create_async_engine(PG_TEST_URL, pool_pre_ping=True)
PgTestSessionLocal = async_sessionmaker(
    bind=pg_test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await pg_test_engine.dispose()


def test_cors_wildcard_forbidden_in_settings():
    """
    CORS in production: if origins contains '*' together with credentials,
    Settings validation MUST raise ValueError with a clear error message.
    """
    with pytest.raises(ValueError, match="Insecure CORS configuration: Wildcard '\\*' in CORS_ORIGINS is forbidden"):
        Settings(CORS_ORIGINS=["*"])

    with pytest.raises(ValueError, match="Insecure CORS configuration: Wildcard '\\*' in CORS_ORIGINS is forbidden"):
        Settings(CORS_ORIGINS="*")

    with pytest.raises(ValueError, match="Insecure CORS configuration: Wildcard '\\*' in CORS_ORIGINS is forbidden"):
        Settings(CORS_ORIGINS="https://example.com, *")

    # Allowed valid configurations should not raise
    valid_settings = Settings(CORS_ORIGINS=["https://app.example.com", "http://localhost:3000"])
    assert "https://app.example.com" in valid_settings.CORS_ORIGINS


@pytest.mark.asyncio
async def test_admin_alert_deduplication_in_postgres_across_worker_restart():
    """
    Verifies that admin alert deduplication is stored persistently in PostgreSQL (admin_alerts table).
    Even after a complete restart of the worker (which resets memory state),
    subsequent attempts to send the same alert are suppressed by the DB record.
    """
    unique_key = f"stalled:report_test_{uuid.uuid4().hex[:8]}:run_123"

    async with PgTestSessionLocal() as session:
        # 1. First trigger: alert should be recorded in DB
        from unittest.mock import patch, AsyncMock
        with patch.object(settings, "TELEGRAM_ADMIN_CHAT_ID", 999888), \
             patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_bot_token"), \
             patch("app.services.scheduler_service.telegram_sender.send_message", new_callable=AsyncMock) as mock_send:

            sent_first = await SchedulerService.notify_admin_alert(
                report_name="Test Report Alert",
                report_id="rep_test_db",
                alert_type="Stalled Sending Run",
                detail="Worker stalled for 15m",
                dedup_key=unique_key,
                session_factory=PgTestSessionLocal
            )
            assert sent_first is True
            assert mock_send.call_count == 1

            # Verify it exists in postgres adpulse_test
            saved = await session.scalar(
                select(AdminAlert).where(AdminAlert.alert_key == unique_key)
            )
            assert saved is not None
            assert saved.alert_type == "Stalled Sending Run"

            # 2. Simulate worker restart:
            # Clear any in-memory references, launch new call with session_factory
            sent_second = await SchedulerService.notify_admin_alert(
                report_name="Test Report Alert",
                report_id="rep_test_db",
                alert_type="Stalled Sending Run",
                detail="Worker stalled for 15m (restart attempt)",
                dedup_key=unique_key,
                session_factory=PgTestSessionLocal
            )
            # The second call is suppressed directly by PostgreSQL!
            assert sent_second is False
            assert mock_send.call_count == 1  # No duplicate message sent

            # Cleanup
            await session.execute(delete(AdminAlert).where(AdminAlert.alert_key == unique_key))
            await session.commit()


@pytest.mark.asyncio
async def test_worker_heartbeat_and_health_endpoint():
    """
    Worker records heartbeat timestamp in worker_heartbeats table.
    /health reports:
    - HTTP 503 and 'worker stale' if heartbeat is absent or older than 120s.
    - HTTP 200 and 'ok' if heartbeat was recorded within the last 120s.
    """
    async with PgTestSessionLocal() as session:
        # Override get_db dependency to point to PgTestSessionLocal
        async def override_get_db():
            async with PgTestSessionLocal() as s:
                yield s

        from app.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            # Case A: No heartbeat recorded yet
            await session.execute(delete(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == "scheduler_worker"))
            await session.commit()

            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["worker"]["status"] == "stale"
            assert "no heartbeat recorded" in data["worker"]["message"]

            # Case B: Stale heartbeat (> 120s ago, e.g. 5 minutes ago)
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            session.add(WorkerHeartbeat(worker_name="scheduler_worker", last_heartbeat_at=stale_time))
            await session.commit()

            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["worker"]["status"] == "stale"
            assert "worker stale: last seen" in data["worker"]["message"]

            # Case C: Fresh heartbeat (< 120s ago)
            await SchedulerService.record_worker_heartbeat(
                worker_name="scheduler_worker",
                session_factory=PgTestSessionLocal
            )

            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["worker"]["status"] == "ok"
            assert "heartbeat" in data["worker"]["message"]

        # Cleanup override
        app.dependency_overrides.pop(get_db, None)
