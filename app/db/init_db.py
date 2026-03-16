from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models import Role, RoleName, RoleScope, User, UserRole
from app.models.base import Base


ROLE_SCOPE_MAP: dict[RoleName, RoleScope] = {
    RoleName.SUPERADMIN: RoleScope.COMPANY,
    RoleName.ACCESS_MANAGER: RoleScope.DEPARTMENT,
    RoleName.OWNER: RoleScope.DOCUMENT,
    RoleName.EDITOR: RoleScope.DOCUMENT,
    RoleName.READER: RoleScope.DOCUMENT,
    RoleName.GUEST: RoleScope.DOCUMENT,
}

DEFAULT_ADMIN_EMAIL = "admin@safedoc.com"


async def create_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_defaults(session: AsyncSession) -> None:
    existing_roles = (await session.execute(select(Role))).scalars().all()
    existing_role_names = {role.name for role in existing_roles}

    for role_name, scope in ROLE_SCOPE_MAP.items():
        if role_name not in existing_role_names:
            session.add(Role(name=role_name, scope=scope))

    await session.flush()

    admin = (await session.execute(select(User).where(User.login == settings.default_superadmin_login))).scalar_one_or_none()
    if admin is None:
        admin = User(
            login=settings.default_superadmin_login,
            password_hash=hash_password(settings.default_superadmin_password),
            surname="Админ",
            name="Системный",
            middle_name=None,
            department="IT",
            position="SuperAdmin",
            email=DEFAULT_ADMIN_EMAIL,
            is_superadmin=True,
        )
        session.add(admin)
        await session.flush()
    elif admin.email == "admin@safedoc.local":
        # Backward-compatible repair for previously seeded invalid email.
        admin.email = DEFAULT_ADMIN_EMAIL

    superadmin_role = (await session.execute(select(Role).where(Role.name == RoleName.SUPERADMIN))).scalar_one()
    has_superadmin_role = (
        await session.execute(
            select(UserRole).where(UserRole.user_id == admin.id, UserRole.role_id == superadmin_role.id)
        )
    ).scalar_one_or_none()
    if has_superadmin_role is None:
        session.add(UserRole(user_id=admin.id, role_id=superadmin_role.id, document_id=None))

    await session.commit()

