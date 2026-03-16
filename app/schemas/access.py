from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccessRequestStatus, RoleName


class AccessRequestCreate(BaseModel):
    document_id: int
    requested_role: RoleName
    message: str | None = None


class AccessRequestResolve(BaseModel):
    approve: bool
    resolution_comment: str | None = None


class AccessRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    requester_id: int
    requested_role: RoleName
    status: AccessRequestStatus
    message: str | None
    created_at: datetime


class GrantAccessRequest(BaseModel):
    document_id: int
    user_id: int
    role: RoleName


class RevokeAccessRequest(BaseModel):
    document_id: int
    user_id: int


class PublicLinkCreate(BaseModel):
    expires_at: datetime


class PublicLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    expires_at: datetime

