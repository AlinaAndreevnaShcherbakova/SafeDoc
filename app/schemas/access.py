from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AccessRequestStatus, RoleName

AccessPermission = Literal[
    "preview",
    "download",
    "edit",
    "version_view",
    "version_manage",
    "access_manage",
]


STATUS_RU_MAP: dict[AccessRequestStatus, str] = {
    AccessRequestStatus.PENDING: "На рассмотрении",
    AccessRequestStatus.APPROVED: "Одобрена",
    AccessRequestStatus.REJECTED: "Отклонена",
}


def normalize_permissions(permissions: list[AccessPermission]) -> list[AccessPermission]:
    normalized = set(permissions)
    if "download" in normalized or "edit" in normalized or "version_view" in normalized or "version_manage" in normalized:
        normalized.add("preview")
    if "version_manage" in normalized:
        normalized.add("version_view")

    order: list[AccessPermission] = [
        "preview",
        "download",
        "edit",
        "version_view",
        "version_manage",
        "access_manage",
    ]
    return [permission for permission in order if permission in normalized]


class AccessRequestCreate(BaseModel):
    document_id: int
    requested_permissions: list[AccessPermission] = Field(min_length=1)
    message: str | None = None

    @model_validator(mode="after")
    def _apply_permission_dependencies(self) -> "AccessRequestCreate":
        self.requested_permissions = normalize_permissions(self.requested_permissions)
        return self


class AccessRequestResolve(BaseModel):
    approve: bool
    resolution_comment: str | None = None


class AccessRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    requester_id: int
    requester_login: str | None = None
    requested_role: RoleName
    requested_permissions: list[AccessPermission] = Field(default_factory=list)
    status: AccessRequestStatus
    status_ru: str
    message: str | None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by_id: int | None = None
    resolved_by_login: str | None = None
    resolution_comment: str | None = None


class GrantAccessRequest(BaseModel):
    document_id: int
    user_id: int
    permissions: list[AccessPermission] = Field(default_factory=list)
    role: RoleName | None = None

    @model_validator(mode="after")
    def _apply_permission_dependencies(self) -> "GrantAccessRequest":
        if not self.permissions and self.role is not None:
            role_permissions_map: dict[RoleName, list[AccessPermission]] = {
                RoleName.SUPERADMIN: ["preview", "download", "edit", "version_view", "version_manage", "access_manage"],
                RoleName.ACCESS_MANAGER: ["preview", "download", "access_manage"],
                RoleName.OWNER: ["preview", "download", "edit", "version_view", "version_manage", "access_manage"],
                RoleName.EDITOR: ["preview", "download", "edit", "version_view", "version_manage"],
                RoleName.READER: ["preview", "download", "version_view"],
                RoleName.GUEST: ["preview"],
            }
            self.permissions = role_permissions_map.get(self.role, ["preview"])
        if not self.permissions:
            raise ValueError("Нужно выбрать хотя бы один уровень доступа")
        self.permissions = normalize_permissions(self.permissions)
        return self


class RevokeAccessRequest(BaseModel):
    document_id: int
    user_id: int


class PublicLinkCreate(BaseModel):
    expires_at: datetime

    @model_validator(mode="after")
    def _validate_expiration(self) -> "PublicLinkCreate":
        if self.expires_at <= datetime.now(timezone.utc):
            raise ValueError("Дата и время действия ссылки должны быть в будущем")
        return self


class PublicLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    token: str
    expires_at: datetime
    revoked_at: datetime | None = None

