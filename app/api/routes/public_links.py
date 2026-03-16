from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.routes.documents import can_manage_document_access
from app.db.postgres import get_session
from app.models import Document, PublicLink, User
from app.schemas.access import PublicLinkCreate, PublicLinkRead
from app.services.audit import audit_service
from app.services.storage import storage_service

router = APIRouter()


def _inline_content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode("ascii").strip() or "preview"
    encoded = quote(filename, safe="")
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


@router.post("/{document_id}", response_model=PublicLinkRead)
async def create_public_link(
    document_id: int,
    payload: PublicLinkCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PublicLinkRead:
    document = await session.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")


    token = uuid4().hex
    link = PublicLink(
        document_id=document_id,
        token=token,
        created_by_id=current_user.id,
        expires_at=payload.expires_at,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)

    await audit_service.log_event("public_link", str(current_user.id), f"create:{document_id}", "success")
    return PublicLinkRead.model_validate(link)


@router.get("/public/{token}")
async def download_by_public_link(token: str, session: AsyncSession = Depends(get_session)) -> Response:
    link = (
        await session.execute(
            select(PublicLink).where(and_(PublicLink.token == token, PublicLink.revoked_at.is_(None)))
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена")

    if link.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Срок действия ссылки истек")

    document = await session.get(Document, link.document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    data = await storage_service.download(document.storage_key)
    return Response(content=data, media_type=document.mime, headers={"Content-Disposition": _inline_content_disposition(document.name)})


@router.post("/public/{token}/revoke")
async def revoke_public_link(
    token: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    link = (await session.execute(select(PublicLink).where(PublicLink.token == token))).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена")

    document = await session.get(Document, link.document_id)
    if document is None or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await can_manage_document_access(session, current_user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    link.revoked_at = datetime.now(timezone.utc)
    await session.commit()

    await audit_service.log_event("public_link", str(current_user.id), f"revoke:{document.id}", "success")
    return {"status": "ok"}

