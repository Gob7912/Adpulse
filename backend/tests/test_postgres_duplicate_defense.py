import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal, engine
from app.models.report import Report
from app.models.run_history import RunHistory
from app.models.user import User
from app.services.scheduler_service import SchedulerService


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_partial_unique_index_blocks_duplicate_sending_and_success():
    """
    Direct integration test against real PostgreSQL (docker compose adpulse-db).
    Verifies that the partial unique index 'uq_run_histories_report_period_success'
    enforces uniqueness for (report_id, period_start, period_end) when:
    is_test = False AND status IN ('success', 'no_data', 'sending').
    """
    async with AsyncSessionLocal() as session:
        # Check database engine dialect is PostgreSQL
        bind = session.get_bind()
        assert bind.dialect.name == "postgresql", f"Expected postgresql dialect, got {bind.dialect.name}"

        # Setup test user and report
        test_email = f"pg_test_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=test_email,
            hashed_password="fake_hashed_pw",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

        report = Report(
            user_id=user_id,
            name="PG Index Test Report",
            meta_account_id="act_test_pg",
            meta_account_name="PG Test Account",
            periodicity="daily",
            account_timezone="Asia/Tashkent"
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        report_id = report.id

        period_s = "2026-08-01"
        period_e = "2026-08-01"

        try:
            # 1. Insert first run with status='sending', is_test=False
            run1 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=False,
                status="sending",
                metrics_data={"spend": 10.0}
            )
            session.add(run1)
            await session.commit()
            await session.refresh(run1)
            run1_id = run1.id

            # 2. Attempt to insert second run for the same period with status='sending', is_test=False
            run2 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=False,
                status="sending",
                metrics_data={"spend": 10.0}
            )
            session.add(run2)

            # In real PostgreSQL, this MUST raise IntegrityError on the partial unique index
            with pytest.raises(IntegrityError) as exc_info:
                await session.commit()

            assert "uq_run_histories_report_period_success" in str(exc_info.value)
            await session.rollback()

            # 3. Transition run1 to status='failed'
            run1_db = await session.scalar(select(RunHistory).where(RunHistory.id == run1_id))
            run1_db.status = "failed"
            await session.commit()

            # 4. Now inserting a new 'sending' run for the same period succeeds!
            run3 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=False,
                status="sending",
                metrics_data={"spend": 10.0}
            )
            session.add(run3)
            await session.commit()
            await session.refresh(run3)
            assert run3.id is not None

            # 5. Transition run3 to 'success'
            run3.status = "success"
            await session.commit()

            # 6. Attempt another 'sending' while one is 'success' -> must fail
            run4 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=False,
                status="sending",
                metrics_data={"spend": 12.0}
            )
            session.add(run4)
            with pytest.raises(IntegrityError) as exc_info2:
                await session.commit()
            assert "uq_run_histories_report_period_success" in str(exc_info2.value)
            await session.rollback()

        finally:
            # Cleanup test artifacts from PostgreSQL
            await session.execute(delete(RunHistory).where(RunHistory.report_id == report_id))
            await session.execute(delete(Report).where(Report.id == report_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_postgres_partial_unique_index_allows_multiple_is_test_runs():
    """
    Verifies against real PostgreSQL that runs with is_test = True are excluded
    from the partial unique index and do NOT block each other.
    """
    async with AsyncSessionLocal() as session:
        test_email = f"pg_test_live_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=test_email,
            hashed_password="fake_hashed_pw",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

        report = Report(
            user_id=user_id,
            name="PG Live Runs Report",
            meta_account_id="act_test_live",
            meta_account_name="PG Test Account Live",
            periodicity="daily",
            account_timezone="Asia/Tashkent"
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        report_id = report.id

        period_s = "2026-08-02"
        period_e = "2026-08-02"

        try:
            # Insert first test run (is_test=True, status="success")
            run1 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=True,
                status="success",
                metrics_data={"spend": 5.0}
            )
            session.add(run1)
            await session.commit()

            # Insert second test run for exact same report and period (is_test=True, status="success")
            # Should NOT raise any IntegrityError because is_test=True is ignored by partial index
            run2 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=True,
                status="success",
                metrics_data={"spend": 5.0}
            )
            session.add(run2)
            await session.commit()
            await session.refresh(run2)
            assert run2.id is not None

            # Insert a third test run (is_test=True, status="sending")
            run3 = RunHistory(
                report_id=report_id,
                user_id=user_id,
                period_type="daily",
                period_start=period_s,
                period_end=period_e,
                is_test=True,
                status="sending",
                metrics_data={"spend": 5.0}
            )
            session.add(run3)
            await session.commit()
            await session.refresh(run3)
            assert run3.id is not None

        finally:
            await session.execute(delete(RunHistory).where(RunHistory.report_id == report_id))
            await session.execute(delete(Report).where(Report.id == report_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_postgres_cleanup_old_raw_snapshots_real_db():
    """
    Verifies that SchedulerService.cleanup_old_raw_snapshots(days=90) against real PostgreSQL:
    1. Sets raw_meta_snapshot = NULL for records with run_at < now - 90 days.
    2. Preserves raw_meta_snapshot for records within the 90-day retention window.
    3. Leaves metrics_data and other fields intact.
    """
    async with AsyncSessionLocal() as session:
        test_email = f"pg_test_clean_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=test_email,
            hashed_password="fake_hashed_pw",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

        report = Report(
            user_id=user_id,
            name="PG Clean Test Report",
            meta_account_id="act_test_clean",
            meta_account_name="PG Test Account Clean",
            periodicity="daily",
            account_timezone="Asia/Tashkent"
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        report_id = report.id

        now_utc = datetime.now(timezone.utc)
        dt_old = now_utc - timedelta(days=95)
        dt_recent = now_utc - timedelta(days=10)

        try:
            # 1. Old record (95 days ago) with snapshot
            old_run = RunHistory(
                report_id=report_id,
                user_id=user_id,
                run_at=dt_old,
                period_type="daily",
                period_start="2026-06-01",
                period_end="2026-06-01",
                is_test=False,
                status="success",
                metrics_data={"spend": 50.0},
                telegram_message_id=12345,
                raw_meta_snapshot={"account_insight": {"spend": "50.00"}, "fetched_at": dt_old.isoformat()}
            )
            # 2. Recent record (10 days ago) with snapshot
            recent_run = RunHistory(
                report_id=report_id,
                user_id=user_id,
                run_at=dt_recent,
                period_type="daily",
                period_start="2026-09-24",
                period_end="2026-09-24",
                is_test=False,
                status="success",
                metrics_data={"spend": 75.0},
                telegram_message_id=67890,
                raw_meta_snapshot={"account_insight": {"spend": "75.00"}, "fetched_at": dt_recent.isoformat()}
            )
            session.add_all([old_run, recent_run])
            await session.commit()
            await session.refresh(old_run)
            await session.refresh(recent_run)
            old_run_id = old_run.id
            recent_run_id = recent_run.id

            # Execute real cleanup in PostgreSQL
            cleaned_count = await SchedulerService.cleanup_old_raw_snapshots(days=90)
            assert cleaned_count >= 1

            # Verify in PostgreSQL
            session.expire_all()
            old_in_db = await session.scalar(select(RunHistory).where(RunHistory.id == old_run_id))
            recent_in_db = await session.scalar(select(RunHistory).where(RunHistory.id == recent_run_id))

            # Old record: raw_meta_snapshot cleaned to NULL, history entry preserved completely
            assert old_in_db.raw_meta_snapshot is None
            assert old_in_db.status == "success"
            assert old_in_db.metrics_data == {"spend": 50.0}
            assert old_in_db.telegram_message_id == 12345

            # Recent record: raw_meta_snapshot and history retained
            assert recent_in_db.raw_meta_snapshot is not None
            assert recent_in_db.raw_meta_snapshot["account_insight"]["spend"] == "75.00"
            assert recent_in_db.status == "success"
            assert recent_in_db.metrics_data == {"spend": 75.0}
            assert recent_in_db.telegram_message_id == 67890

        finally:
            await session.execute(delete(RunHistory).where(RunHistory.report_id == report_id))
            await session.execute(delete(Report).where(Report.id == report_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
