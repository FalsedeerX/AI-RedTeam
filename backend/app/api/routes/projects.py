from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.projects import ProjectDetail, ProjectSummary
from app.api.deps import get_current_user_id


router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectsRouter:
    def __init__(self):
        self.router = router
        self.router.get("", response_model=list[ProjectSummary])(self.list_projects)
        self.router.post("/create", response_model=ProjectDetail)(self.create_project)
        self.router.get("/{project_id}", response_model=ProjectDetail)(self.get_project)

    def list_projects(self, user_id: UUID = Depends(get_current_user_id)):
        """ Recevie a list of project the current user owns """
        pass

    def create_project(self, user_id: UUID = Depends(get_current_user_id)):
        """ Create a new project for the current user """
        pass

    def get_project(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """ Receive details for a speicifc project id """
        pass
