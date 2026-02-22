from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.domain.projects import ProjectStatus


class ProjectCreate(BaseModel):
    """ Request for project creation """
    name: str
    description: str | None = None


class ProjectSummary(BaseModel):
    """ Response for retrieving a brief project view """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    project_status: ProjectStatus
    description: str | None = None


class ProjectDetail(BaseModel):
    """ Response for retrieving the complete information of a project """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    project_status: ProjectStatus
    description: str | None = None
    target_ids: list[UUID] = []
    run_ids: list[UUID] = []
    report_id: UUID | None = None
