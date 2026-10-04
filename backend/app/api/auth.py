
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.security import (
    auth_rate_limiter,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

def _build_user_response(user: User) -> UserResponse:
    has_meta = bool(user.meta_connection and user.meta_connection.encrypted_access_token)
    is_valid = bool(user.meta_connection.is_valid) if (user.meta_connection and has_meta) else True
    meta_name = user.meta_connection.meta_user_name if user.meta_connection else None
    meta_avatar = user.meta_connection.meta_avatar_url if user.meta_connection else None
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        has_meta_connection=has_meta,
        is_meta_valid=is_valid,
        meta_user_name=meta_name,
        meta_avatar_url=meta_avatar
    )

@router.post("/register", response_model=TokenResponse)
async def register(
    data: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Регистрация новых пользователей временно приостановлена администратором."
        )

    # Check if email is already taken
    existing = await db.execute(select(User).where(User.email == data.email.lower().strip()))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован."
        )

    new_user = User(
        email=data.email.lower().strip(),
        hashed_password=hash_password(data.password),
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="adpulse_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_build_user_response(new_user)
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{data.email.lower().strip()}"

    if auth_rate_limiter.is_rate_limited(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много неудачных попыток входа. Пожалуйста, подождите минуту перед повторной попыткой."
        )

    query = select(User).where(User.email == data.email.lower().strip())
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not verify_password(data.password, user.hashed_password):
        auth_rate_limiter.record_attempt(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован."
        )

    # Success, reset rate limit
    auth_rate_limiter.reset(rate_limit_key)

    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="adpulse_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_build_user_response(user)
    )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="adpulse_token")
    return {"message": "Успешный выход из системы"}

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return _build_user_response(user)

@router.delete("/me")
async def delete_account(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """'Delete my account and all data' action."""
    await db.delete(user)
    await db.commit()
    response.delete_cookie(key="adpulse_token")
    return {"message": "Аккаунт и все связанные отчёты, подключения и данные успешно удалены."}
