from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_role_names
from app.db.postgres import get_session
from app.models import Document, DocumentVersion, Role, RoleName, User, UserRole, Visibility
from app.schemas.documents import DocumentRead, VersionRead
from app.services.audit import audit_service
from app.services.authz import (
    is_read_allowed_by_visibility,
    is_write_allowed_by_visibility,
    role_can_manage_access,
    role_can_read,
    role_can_write,
)
from app.services.storage import storage_service
from app.services.preview import preview_service

router = APIRouter()

MAX_FILE_SIZE = 300 * 1024 * 1024


def _build_content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode("ascii").strip() or "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


async def _can_read_document(session: AsyncSession, current_user: User, document: Document) -> bool:
    if current_user.id == document.owner_id:
        return True
    roles = await get_user_role_names(current_user.id, session, document.id)
    return role_can_read(roles) or is_read_allowed_by_visibility(document.visibility)


async def _can_write_document(session: AsyncSession, current_user: User, document: Document) -> bool:
    if current_user.id == document.owner_id:
        return True
    roles = await get_user_role_names(current_user.id, session, document.id)
    return role_can_write(roles) or is_write_allowed_by_visibility(document.visibility)


async def can_manage_document_access(session: AsyncSession, current_user: User, document: Document) -> bool:
    if current_user.id == document.owner_id:
        return True
    roles = await get_user_role_names(current_user.id, session, document.id)
    return role_can_manage_access(roles)


@router.post("", response_model=DocumentRead)
async def upload_document(
    file: UploadFile = File(...),
    visibility: Visibility = Form(Visibility.BY_REQUEST),
    comment: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл больше 300 МБ")

    storage_key = await storage_service.upload(file.filename, data, metadata={"owner_id": current_user.id, "version": 1})

    doc = Document(
        name=file.filename,
        owner_id=current_user.id,
        comment=comment,
        mime=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        storage_key=storage_key,
        visibility=visibility,
        current_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    await session.flush()

    owner_role = (await session.execute(select(Role).where(Role.name == RoleName.OWNER))).scalar_one()
    existing_owner_acl = (
        await session.execute(
            select(UserRole).where(
                and_(UserRole.user_id == current_user.id, UserRole.role_id == owner_role.id, UserRole.document_id == doc.id)
            )
        )
    ).scalar_one_or_none()
    if existing_owner_acl is None:
        session.add(UserRole(user_id=current_user.id, role_id=owner_role.id, document_id=doc.id))

    session.add(
        DocumentVersion(
            document_id=doc.id,
            version=1,
            author_id=current_user.id,
            comment=comment,
            storage_key=storage_key,
        )
    )
    await session.commit()
    await session.refresh(doc)

    await audit_service.log_event("document", str(current_user.id), f"upload:{doc.id}", "success")
    return DocumentRead.model_validate(doc)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    query = select(Document).where(Document.deleted_at.is_(None))
    if search:
        query = query.where(Document.name.ilike(f"%{search}%"))

    docs = (await session.execute(query.order_by(Document.updated_at.desc()))).scalars().all()

    result: list[DocumentRead] = []
    for doc in docs:
        if await _can_read_document(session, current_user, doc):
            result.append(DocumentRead.model_validate(doc))
    return result


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_read_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к документу")

    try:
        data = await storage_service.download(doc.storage_key)
    except FileNotFoundError as exc:
        await audit_service.log_event("document", str(current_user.id), f"download:{doc.id}", "error", str(exc))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл документа не найден в хранилище") from exc
    except ValueError as exc:
        await audit_service.log_event("document", str(current_user.id), f"download:{doc.id}", "error", str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Поврежден ключ хранения документа") from exc

    await audit_service.log_event("document", str(current_user.id), f"download:{doc.id}", "success")
    return Response(content=data, media_type=doc.mime, headers={"Content-Disposition": _build_content_disposition(doc.name)})


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_read_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к документу")

    data = await storage_service.download(doc.storage_key)
    await audit_service.log_event("document", str(current_user.id), f"preview:{doc.id}", "success")
    return await preview_service.build_preview_response(data=data, mime=doc.mime, filename=doc.name)


@router.post("/{document_id}/versions", response_model=VersionRead)
async def upload_new_version(
    document_id: int,
    file: UploadFile = File(...),
    comment: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> VersionRead:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_write_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для редактирования")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл больше 300 МБ")

    new_version = doc.current_version + 1
    storage_key = await storage_service.upload(file.filename, data, metadata={"doc_id": doc.id, "version": new_version})

    doc.storage_key = storage_key
    doc.size_bytes = len(data)
    doc.mime = file.content_type or "application/octet-stream"
    doc.current_version = new_version
    doc.updated_at = datetime.now(timezone.utc)

    version = DocumentVersion(
        document_id=doc.id,
        version=new_version,
        author_id=current_user.id,
        comment=comment,
        storage_key=storage_key,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)

    await audit_service.log_event("document", str(current_user.id), f"new_version:{doc.id}:{new_version}", "success")
    return VersionRead.model_validate(version)


@router.get("/{document_id}/versions", response_model=list[VersionRead])
async def list_versions(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[VersionRead]:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_read_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к документу")

    versions = (
        await session.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.desc())
        )
    ).scalars().all()
    return [VersionRead.model_validate(version) for version in versions]


@router.patch("/{document_id}/rename", response_model=DocumentRead)
async def rename_document(
    document_id: int,
    name: str = Form(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_write_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    doc.name = name
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)

    await audit_service.log_event("document", str(current_user.id), f"rename:{doc.id}", "success")
    return DocumentRead.model_validate(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_write_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    doc.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    await audit_service.log_event("document", str(current_user.id), f"delete:{doc.id}", "success")
    return {"status": "ok"}


@router.post("/{document_id}/restore/{version}", response_model=DocumentRead)
async def restore_version(
    document_id: int,
    version: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    doc = await session.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if not await _can_write_document(session, current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    target_version = (
        await session.execute(
            select(DocumentVersion).where(
                and_(DocumentVersion.document_id == document_id, DocumentVersion.version == version)
            )
        )
    ).scalar_one_or_none()
    if target_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Версия не найдена")

    doc.storage_key = target_version.storage_key
    doc.current_version = target_version.version
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)

    await audit_service.log_event("document", str(current_user.id), f"restore:{doc.id}:{version}", "success")
    return DocumentRead.model_validate(doc)

