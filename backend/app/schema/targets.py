from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.domain.target import TargetType


class TargetCreate(BaseModel):
    """ Request for target creation """
    project_id: UUID
    target_type: TargetType
    label: str | None = None
    value: str


class TargetDetail(BaseModel):
    """ Response for asking for a target's detail information """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    value: str
    label: str | None = None
    target_type: TargetType
    created_at: datetime


class TargetPatch(BaseModel):
    """ Request for patching an existing target """
    model_config = ConfigDict(extra="forbid")

    value: str | None = None
    label: str | None = None
    target_type: TargetType | None
