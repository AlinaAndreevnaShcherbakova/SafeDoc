from datetime import datetime, timezone
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_role_names
from app.api.routes.documents import can_manage_document_access
from app.db.postgres import get_session
from app.models import AccessRequest, AccessRequestStatus, Document, Role, RoleName, User, UserRole
from app.schemas.access import (
    STATUS_RU_MAP,
    AccessPermission,
    AccessRequestCreate,
    AccessRequestRead,
    AccessRequestResolve,
    GrantAccessRequest,
    RevokeAccessRequest,
    normalize_permissions,
)
from app.services.audit import audit_service
from app.services.notifications import notification_service
from app.services.authz import role_can_manage_access

router = APIRouter()

PERM_PREFIX = "__perms__:"


def _permissions_to_role(permissions: Iterable[AccessPermission]) -> RoleName:
    permissions_set = set(permissions)
    if "access_manage" in permissions_set:
        return RoleName.OWNER
    if "edit" in permissions_set or "version_manage" in permissions_set:
        return RoleName.EDITOR
    if "preview" in permissions_set or "download" in permissions_set or "version_view" in permissions_set:
        return RoleName.READER
    return RoleName.GUEST


def _role_to_permissions(role: RoleName) -> list[AccessPermission]:
    if role in {RoleName.SUPERADMIN, RoleName.OWNER}:
        return normalize_permissions(["preview", "download", "edit", "version_view", "version_manage", "access_manage"])
    if role == RoleName.EDITOR:
        return normalize_permissions(["preview", "download", "edit", "version_view", "version_manage"])
    if role == RoleName.READER:
        return normalize_permissions(["preview", "download", "version_view"])
    if role == RoleName.GUEST:
        return ["preview"]
    return ["preview"]


def _pack_message_with_permissions(message: str | None, permissions: list[AccessPermission]) -> str:
    base = (message or "").strip()
    return f"{PERM_PREFIX}{','.join(permissions)}\n{base}" if base else f"{PERM_PREFIX}{','.join(permissions)}"


def _unpack_message_and_permissions(raw_message: str | None, requested_role: RoleName) -> tuple[str | None, list[AccessPermission]]:
    if not raw_message:
        return None, _role_to_permissions(requested_role)

    if not raw_message.startswith(PERM_PREFIX):
        return raw_message, _role_to_permissions(requested_role)

    first_line, _, rest = raw_message.partition("\n")
    packed = first_line[len(PERM_PREFIX):]
    parsed = [part for part in packed.split(",") if part]
    try:
        permissions = normalize_permissions(parsed)  # type: ignore[arg-type]
    except Exception:
        permissions = _role_to_permissions(requested_role)
    clean_message = rest.strip() or None
    return clean_message, permissions


async def _serialize_access_request(session: AsyncSession, request: AccessRequest) -> AccessRequestRead:
    requester = await session.get(User, request.requester_id)
    resolver = await session.get(User, request.resolved_by_id) if request.resolved_by_id else None
    message, permissions = _unpack_message_and_permissions(request.message, request.requested_role)

    payload = AccessRequestRead.model_validate(request).model_copy(
        update={
            "requester_login": requester.login if requester else None,
            "resolved_by_login": resolver.login if resolver else None,
            "status_ru": STATUS_RU_MAP.get(request.status, request.status.value),
            "message": message,
            "requested_permissions": permissions,
        }
    )
    return payload


@router.post("/requests", response_model=AccessRequestRead)
async def request_access(
    payload: AccessRequestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccessRequestRead:
    doc = await session.get(Document, payload.document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    request = AccessRequest(
        document_id=payload.document_id,
        requester_id=current_user.id,
        requested_role=_permissions_to_role(payload.requested_permissions),
        status=AccessRequestStatus.PENDING,
        message=_pack_message_with_permissions(payload.message, payload.requested_permissions),
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)

    owner = await session.get(User, doc.owner_id)
    if owner is not None:
        notification_service.send_email(
            owner.email,
            "Запрос на доступ к файлу",
            f"Пользователь {current_user.login} запросил доступ к файлу {doc.name}",
        )

    await audit_service.log_event("access_request", str(current_user.id), f"create:{request.id}", "success")
    return await _serialize_access_request(session, request)


@router.get("/requests/my", response_model=list[AccessRequestRead])
async def my_requests(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AccessRequestRead]:
    rows = (
        await session.execute(
            select(AccessRequest).where(AccessRequest.requester_id == current_user.id).order_by(AccessRequest.created_at.desc())
        )
    ).scalars().all()
    return [await _serialize_access_request(session, row) for row in rows]


@router.get("/requests/inbox", response_model=list[AccessRequestRead])
async def inbox_requests(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AccessRequestRead]:
    role_names = await get_user_role_names(current_user.id, session)
    if not (current_user.is_superadmin or role_can_manage_access(role_names)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if current_user.is_superadmin or RoleName.ACCESS_MANAGER in role_names:
        rows = (
            await session.execute(
                select(AccessRequest)
                .order_by(AccessRequest.created_at.desc())
            )
        ).scalars().all()
    else:
        owned_doc_ids = (await session.execute(select(Document.id).where(Document.owner_id == current_user.id))).scalars().all()
        if not owned_doc_ids:
            return []
        rows = (
            await session.execute(
                select(AccessRequest)
                .where(
                    AccessRequest.document_id.in_(owned_doc_ids)
                )
                .order_by(AccessRequest.created_at.desc())
            )
        ).scalars().all()

    return [await _serialize_access_request(session, row) for row in rows]


@router.post("/requests/{request_id}/resolve", response_model=AccessRequestRead)
async def resolve_request(
    request_id: int,
    payload: AccessRequestResolve,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccessRequestRead:
    access_request = await session.get(AccessRequest, request_id)
    if access_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрос не найден")

    document = await session.get(Document, access_request.document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    access_request.status = AccessRequestStatus.APPROVED if payload.approve else AccessRequestStatus.REJECTED
    access_request.resolved_at = datetime.now(timezone.utc)
    access_request.resolved_by_id = current_user.id
    access_request.resolution_comment = payload.resolution_comment

    if payload.approve:
        role = (await session.execute(select(Role).where(Role.name == access_request.requested_role))).scalar_one()
        existing = (
            await session.execute(
                select(UserRole).where(
                    and_(
                        UserRole.user_id == access_request.requester_id,
                        UserRole.document_id == access_request.document_id,
                        UserRole.role_id == role.id,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(UserRole(user_id=access_request.requester_id, role_id=role.id, document_id=access_request.document_id))

    await session.commit()
    await session.refresh(access_request)

    requester = await session.get(User, access_request.requester_id)
    if requester is not None:
        notification_service.send_email(
            requester.email,
            "Статус заявки на доступ",
            f"Ваш запрос к документу #{access_request.document_id} обработан: {STATUS_RU_MAP.get(access_request.status, access_request.status.value)}",
        )

    await audit_service.log_event("access_request", str(current_user.id), f"resolve:{access_request.id}", "success")
    return await _serialize_access_request(session, access_request)


@router.post("/grant")
async def grant_access(
    payload: GrantAccessRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    document = await session.get(Document, payload.document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    role_name = _permissions_to_role(payload.permissions)
    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Роль не найдена")

    current_rows = (
        await session.execute(
            select(UserRole).where(
                and_(UserRole.user_id == payload.user_id, UserRole.document_id == payload.document_id)
            )
        )
    ).scalars().all()
    for row in current_rows:
        await session.delete(row)

    session.add(UserRole(user_id=payload.user_id, role_id=role.id, document_id=payload.document_id))
    await session.commit()

    await audit_service.log_event("acl", str(current_user.id), f"grant:{payload.document_id}:{payload.user_id}", "success")
    return {"status": "ok"}


@router.post("/revoke")
async def revoke_access(
    payload: RevokeAccessRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    document = await session.get(Document, payload.document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    roles = (
        await session.execute(
            select(UserRole).where(
                and_(UserRole.user_id == payload.user_id, UserRole.document_id == payload.document_id)
            )
        )
    ).scalars().all()

    for row in roles:
        await session.delete(row)

    await session.commit()

    revoked_user = await session.get(User, payload.user_id)
    if revoked_user is not None:
        notification_service.send_email(
            revoked_user.email,
            "Доступ к файлу изменен",
            f"Ваш доступ к документу #{payload.document_id} был отозван.",
        )

    await audit_service.log_event("acl", str(current_user.id), f"revoke:{payload.document_id}:{payload.user_id}", "success")
    return {"status": "ok"}

