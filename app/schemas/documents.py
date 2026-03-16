from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Visibility


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    mime: str
    size_bytes: int
    visibility: Visibility
    current_version: int
    created_at: datetime
    updated_at: datetime


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version: int
    author_id: int
    comment: str | None
    created_at: datetime

