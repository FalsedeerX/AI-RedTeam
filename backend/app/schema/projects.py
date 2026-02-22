from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.domain.projects import ProjectStatus


class ProjectCreate(BaseModel):
    """ project creation """
    project_name: str
    project_description: str


class ProjectInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    status: ProjectStatus
