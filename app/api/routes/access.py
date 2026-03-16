from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_role_names
from app.api.routes.documents import can_manage_document_access
from app.db.postgres import get_session
from app.models import AccessRequest, AccessRequestStatus, Document, Role, RoleName, User, UserRole
from app.schemas.access import AccessRequestCreate, AccessRequestRead, AccessRequestResolve, GrantAccessRequest, RevokeAccessRequest
from app.services.audit import audit_service
from app.services.notifications import notification_service
from app.services.authz import role_can_manage_access

router = APIRouter()


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
        requested_role=payload.requested_role,
        status=AccessRequestStatus.PENDING,
        message=payload.message,
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
    return AccessRequestRead.model_validate(request)


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
    return [AccessRequestRead.model_validate(row) for row in rows]


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
                .where(AccessRequest.status == AccessRequestStatus.PENDING)
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
                    and_(
                        AccessRequest.status == AccessRequestStatus.PENDING,
                        AccessRequest.document_id.in_(owned_doc_ids),
                    )
                )
                .order_by(AccessRequest.created_at.desc())
            )
        ).scalars().all()

    return [AccessRequestRead.model_validate(row) for row in rows]


@router.post("/requests/{request_id}/resolve", response_model=AccessRequestRead)
async def resolve_request(
    request_id: int,
    payload: AccessRequestResolve,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccessRequestRead:
    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрос не найден")

    doc = await session.get(Document, request.document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    request.status = AccessRequestStatus.APPROVED if payload.approve else AccessRequestStatus.REJECTED
    request.resolved_at = datetime.now(timezone.utc)
    request.resolved_by_id = current_user.id
    request.resolution_comment = payload.resolution_comment

    if payload.approve:
        role = (await session.execute(select(Role).where(Role.name == request.requested_role))).scalar_one()
        existing = (
            await session.execute(
                select(UserRole).where(
                    and_(
                        UserRole.user_id == request.requester_id,
                        UserRole.document_id == request.document_id,
                        UserRole.role_id == role.id,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(UserRole(user_id=request.requester_id, role_id=role.id, document_id=request.document_id))

    await session.commit()
    await session.refresh(request)

    requester = await session.get(User, request.requester_id)
    if requester is not None:
        notification_service.send_email(
            requester.email,
            "Статус заявки на доступ",
            f"Ваш запрос к документу #{request.document_id} обработан: {request.status.value}",
        )

    await audit_service.log_event("access_request", str(current_user.id), f"resolve:{request.id}", "success")
    return AccessRequestRead.model_validate(request)


@router.post("/grant")
async def grant_access(
    payload: GrantAccessRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    doc = await session.get(Document, payload.document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    role = (await session.execute(select(Role).where(Role.name == payload.role))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Роль не найдена")

    exists = (
        await session.execute(
            select(UserRole).where(
                and_(
                    UserRole.user_id == payload.user_id,
                    UserRole.document_id == payload.document_id,
                    UserRole.role_id == role.id,
                )
            )
        )
    ).scalar_one_or_none()
    if exists is None:
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
    doc = await session.get(Document, payload.document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, doc):
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

