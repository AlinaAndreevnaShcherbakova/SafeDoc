from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_superadmin
from app.core.security import hash_password
from app.db.postgres import get_session
from app.models import User
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.services.audit import audit_service

router = APIRouter()


@router.post("", response_model=UserRead)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superadmin),
) -> UserRead:
    if payload.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Создание пользователей с правами суперадмина запрещено",
        )

    exists = (await session.execute(select(User).where((User.login == payload.login) | (User.email == payload.email)))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким логином или email уже существует")

    user = User(
        login=payload.login,
        password_hash=hash_password(payload.password),
        surname=payload.surname,
        name=payload.name,
        middle_name=payload.middle_name,
        department=payload.department,
        position=payload.position,
        email=str(payload.email),
        is_superadmin=False,
    )
    session.add(user)

    await session.commit()
    await session.refresh(user)
    await audit_service.log_event("users", str(user.id), "create", "success")
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superadmin),
) -> list[UserRead]:
    users = (await session.execute(select(User).order_by(User.id))).scalars().all()
    return [UserRead.model_validate(user) for user in users]


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superadmin),
) -> UserRead:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if payload.is_superadmin is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменять флаг суперадминистратора",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "password":
            user.password_hash = hash_password(value)
        elif value is not None:
            setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    await audit_service.log_event("users", str(user.id), "update", "success")
    return UserRead.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_superadmin),
) -> dict:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователя-суперадмина нельзя удалить")

    await session.delete(user)
    await session.commit()
    await audit_service.log_event("users", str(user_id), "delete", "success")
    return {"status": "ok"}
