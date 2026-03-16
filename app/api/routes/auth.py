from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.postgres import get_session
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.users import UserRead
from app.services.audit import audit_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    user = (await session.execute(select(User).where(User.login == payload.login))).scalar_one_or_none()
    if user is None:
        await audit_service.log_event("auth", payload.login, "login", "error", "user_not_found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    now = datetime.now(timezone.utc)
    if user.lock_until and user.lock_until > now:
        await audit_service.log_event("auth", str(user.id), "login", "error", "account_locked")
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Форма входа заблокирована на 10 минут")

    if not verify_password(payload.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= 3:
            user.lock_until = now + timedelta(minutes=10)
        await session.commit()
        await audit_service.log_event("auth", str(user.id), "login", "error", "invalid_password")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    user.failed_logins = 0
    user.lock_until = None
    await session.commit()

    token = create_access_token(subject=str(user.id))
    await audit_service.log_event("auth", str(user.id), "login", "success")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)

