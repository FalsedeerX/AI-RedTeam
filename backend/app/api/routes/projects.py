from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.projects import ProjectCreate, ProjectSummary, ProjectDetail
from app.api.deps import get_current_user_id
from app.db.broker import ProjectsBroker

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectsRouter:
    def __init__(self):
        self.router = router
        self.broker = ProjectsBroker()
        self.router.get("", response_model=list[ProjectSummary])(self.list_projects)
        self.router.post("", response_model=ProjectSummary)(self.create_project)
        self.router.delete("/{project_id}", status_code=204)(self.delete_project)
        self.router.get("/{project_id}", response_model=ProjectDetail)(self.get_project)

    def list_projects(self, user_id: UUID = Depends(get_current_user_id)):
        """ Recevie a list of project the current user owns """
        return self.broker.list_by_owner(user_id)

    def create_project(self, payload: ProjectCreate, user_id: UUID = Depends(get_current_user_id)):
        """ Create a new project for the current user """
        project_entry = self.broker.create(
            {
                "name": payload.name,
                "description": payload.description,
                "owner_id": user_id
            }
        )
        return project_entry

    def delete_project(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """ Delete a project by specified project id """
        project_entry = self.broker.get(project_id)
        if not project_entry: raise HTTPException(status_code=404, detail="Project not found")

        # check if the user actually owned the project
        if project_entry.owner_id != user_id: raise HTTPException(status_code=404, detail="Project not found")
        self.broker.purge(project_id)

    def get_project(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """ Receive details for a speicifc project id """
        project_entry = self.broker.get(project_id)
        if not project_entry: raise HTTPException(status_code=404, detail="Project not found")
        if project_entry.owner_id != user_id: raise HTTPException(status_code=404, detail="Project not found")

        # create the dto to return
        dto = ProjectDetail.model_validate(project_entry)
        dto.target_ids = [t.id for t in self.broker.list_targets(project_id)]
        dto.run_ids = [r.id for r in self.broker.list_runs(project_id)]
        dto.report_ids = [r.id for r in self.broker.list_reports(project_id)]
        return dto


if __name__ == "__main__":
    pass
