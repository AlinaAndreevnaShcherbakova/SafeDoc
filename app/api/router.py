from fastapi import APIRouter

from app.api.routes import access, auth, audit, documents, public_links, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(access.router, prefix="/access", tags=["access"])
api_router.include_router(public_links.router, prefix="/links", tags=["links"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])

