from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.report import Report
from app.models.run_history import RunHistory
from app.models.user import User
from app.schemas.history import RunHistoryResponse

router = APIRouter(prefix="/history", tags=["history"])

@router.get("", response_model=list[RunHistoryResponse])
async def get_all_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(RunHistory)
        .where(RunHistory.user_id == user.id)
        .order_by(RunHistory.run_at.desc())
        .limit(100)
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    return [RunHistoryResponse.model_validate(r) for r in rows]

@router.get("/report/{report_id}", response_model=list[RunHistoryResponse])
async def get_report_history(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify report ownership
    rep_res = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if not rep_res.scalars().first():
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    query = (
        select(RunHistory)
        .where(RunHistory.report_id == report_id, RunHistory.user_id == user.id)
        .order_by(RunHistory.run_at.desc())
        .limit(50)
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    return [RunHistoryResponse.model_validate(r) for r in rows]
