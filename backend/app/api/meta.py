from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.meta_connection import MetaConnection
from app.schemas.meta import (
    MetaTokenVerifyRequest,
    MetaProfileResponse,
    MetaAdAccountResponse,
    MetaCampaignResponse,
    MetaMetadataResponse,
    MetaMetricInfo,
    MetaTemplateInfo
)
from app.services.meta_metrics import (
    METRIC_DEFINITIONS,
    TEMPLATES,
    OPTIMIZATION_GOALS
)
from app.services.meta_client import MetaClient, MetaAPIError, MetaTokenExpiredError
from app.security import encrypt_secret, decrypt_secret
from app.api.deps import get_current_user

router = APIRouter(prefix="/meta", tags=["meta"])

@router.get("/metadata", response_model=MetaMetadataResponse)
async def get_metadata():
    metrics = [
        MetaMetricInfo(
            key=m.key,
            category=m.category,
            is_additive=m.is_additive,
            format_type=m.format_type,
            ru_label=m.ru_label,
            uz_label=m.uz_label,
            en_label=m.en_label,
            tooltip_ru=m.tooltip_ru,
            tooltip_uz=m.tooltip_uz,
            tooltip_en=m.tooltip_en,
            is_limited=m.is_limited,
            sample_value=m.sample_value
        )
        for m in METRIC_DEFINITIONS.values()
    ]

    templates = [
        MetaTemplateInfo(
            id=t["id"],
            is_recommended=t["is_recommended"],
            title_ru=t["title_ru"],
            title_uz=t["title_uz"],
            title_en=t["title_en"],
            desc_ru=t["desc_ru"],
            desc_uz=t["desc_uz"],
            desc_en=t["desc_en"],
            metrics=t["metrics"]
        )
        for t in TEMPLATES.values()
    ]

    return MetaMetadataResponse(
        metrics=metrics,
        templates=templates,
        optimization_goals=OPTIMIZATION_GOALS
    )

@router.post("/verify-token", response_model=MetaProfileResponse)
async def verify_and_save_token(
    data: MetaTokenVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    token = data.access_token.strip()
    client = MetaClient(access_token=token)

    try:
        profile_data = await client.verify_token()
    except MetaAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось проверить токен: {str(exc)}"
        )

    # Encrypt token at rest
    encrypted = encrypt_secret(token)

    # Upsert MetaConnection
    query = select(MetaConnection).where(MetaConnection.user_id == user.id)
    result = await db.execute(query)
    conn = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if conn:
        conn.encrypted_access_token = encrypted
        conn.meta_user_id = profile_data.get("meta_user_id")
        conn.meta_user_name = profile_data.get("meta_user_name")
        conn.meta_avatar_url = profile_data.get("meta_avatar_url")
        conn.is_valid = True
        conn.last_verified_at = now_utc
    else:
        conn = MetaConnection(
            user_id=user.id,
            encrypted_access_token=encrypted,
            meta_user_id=profile_data.get("meta_user_id"),
            meta_user_name=profile_data.get("meta_user_name"),
            meta_avatar_url=profile_data.get("meta_avatar_url"),
            is_valid=True,
            last_verified_at=now_utc
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    return MetaProfileResponse(
        meta_user_id=conn.meta_user_id,
        meta_user_name=conn.meta_user_name,
        meta_avatar_url=conn.meta_avatar_url,
        is_valid=conn.is_valid
    )

@router.get("/profile", response_model=MetaProfileResponse)
async def get_meta_profile(user: User = Depends(get_current_user)):
    if not user.meta_connection or not user.meta_connection.is_valid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подключение Meta Ads не найдено."
        )

    return MetaProfileResponse(
        meta_user_id=user.meta_connection.meta_user_id,
        meta_user_name=user.meta_connection.meta_user_name,
        meta_avatar_url=user.meta_connection.meta_avatar_url,
        is_valid=user.meta_connection.is_valid
    )

@router.delete("/connection")
async def disconnect_meta(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.meta_connection:
        await db.delete(user.meta_connection)
        await db.commit()
    return {"message": "Подключение к Meta Ads удалено."}

@router.get("/adaccounts", response_model=list[MetaAdAccountResponse])
async def get_ad_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user.meta_connection or not user.meta_connection.encrypted_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала подключите и сохраните токен доступа Meta Ads."
        )

    try:
        raw_token = decrypt_secret(user.meta_connection.encrypted_access_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка расшифровки токена")

    client = MetaClient(access_token=raw_token)
    try:
        accounts = await client.get_ad_accounts()
        return [
            MetaAdAccountResponse(
                id=a["id"],
                account_id=a["account_id"],
                name=a["name"],
                currency=a["currency"],
                timezone_name=a["timezone_name"],
                account_status=a["account_status"],
                business_name=a.get("business_name")
            )
            for a in accounts
        ]
    except MetaTokenExpiredError as exc:
        if user.meta_connection:
            user.meta_connection.is_valid = False
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except MetaAPIError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/campaigns", response_model=list[MetaCampaignResponse])
async def get_campaigns(
    ad_account_id: str = Query(..., description="Meta Ad Account ID, e.g. act_123456789"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user.meta_connection or not user.meta_connection.encrypted_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен Meta не подключен"
        )

    try:
        raw_token = decrypt_secret(user.meta_connection.encrypted_access_token)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка расшифровки токена")

    client = MetaClient(access_token=raw_token)
    try:
        campaigns = await client.get_campaigns(ad_account_id=ad_account_id)
        return [
            MetaCampaignResponse(
                id=c["id"],
                name=c["name"],
                objective=c.get("objective", "OUTCOME_TRAFFIC"),
                status=c.get("status", "ACTIVE"),
                effective_status=c.get("effective_status", "ACTIVE")
            )
            for c in campaigns
        ]
    except MetaTokenExpiredError as exc:
        if user.meta_connection:
            user.meta_connection.is_valid = False
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except MetaAPIError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
