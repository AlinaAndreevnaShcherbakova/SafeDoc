from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.postgres import get_session
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UpdateProfileRequest
from app.schemas.users import UserRead
from app.services.audit import audit_service

router = APIRouter()


def _serialize_user(user: User) -> UserRead:
    role = "superadmin" if user.is_superadmin else "user"
    return UserRead.model_validate(
        {
            "id": user.id,
            "login": user.login,
            "surname": user.surname,
            "name": user.name,
            "middle_name": user.middle_name,
            "department": user.department,
            "position": user.position,
            "email": user.email,
            "is_superadmin": user.is_superadmin,
            "role": role,
        }
    )


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
    return _serialize_user(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UpdateProfileRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(current_user, field, value)

    await session.commit()
    await session.refresh(current_user)
    await audit_service.log_event("auth", str(current_user.id), "profile_update", "success")
    return _serialize_user(current_user)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текущий пароль указан неверно")

    current_user.password_hash = hash_password(payload.new_password)
    await session.commit()
    await audit_service.log_event("auth", str(current_user.id), "password_change", "success")
    return {"status": "ok"}

