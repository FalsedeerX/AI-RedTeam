from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schema.projects import ProjectCreate, ProjectSummary, ProjectDetail
from app.api.deps import get_current_user_id
from app.db.broker import ProjectsBroker, FindingsBroker, ReportsBroker

router = APIRouter(prefix="/projects", tags=["projects"])


class FindingResponse(BaseModel):
    id: str
    finding_type: str
    severity: str
    title: str
    content: str
    evidence: str
    confidence: int
    run_id: str


class ReportResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    content: str
    report_format: str
    project_id: str
    created_at: str


class ProjectsRouter:
    def __init__(self):
        self.router = router
        self.broker = ProjectsBroker()
        self.findings_broker = FindingsBroker()
        self.reports_broker = ReportsBroker()
        self.router.get("", response_model=list[ProjectSummary])(self.list_projects)
        self.router.post("", status_code=201, response_model=ProjectSummary)(self.create_project)
        self.router.delete("/{project_id}", status_code=204)(self.delete_project)
        self.router.get("/{project_id}", response_model=ProjectDetail)(self.get_project)
        self.router.get("/{project_id}/findings", response_model=list[FindingResponse])(self.get_project_findings)
        self.router.get("/{project_id}/reports", response_model=list[ReportResponse])(self.get_project_reports)

    def list_projects(self, user_id: UUID = Depends(get_current_user_id)):
        """ Recevie a list of projects the current user owns """
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
        deleted = self.broker.purge(project_id)
        if not deleted: raise HTTPException(status_code=404, detail="Project not found")

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

    def get_project_findings(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """Return all findings across every run belonging to this project."""
        project_entry = self.broker.get(project_id)
        if not project_entry: raise HTTPException(status_code=404, detail="Project not found")
        if project_entry.owner_id != user_id: raise HTTPException(status_code=404, detail="Project not found")

        runs = self.broker.list_runs(project_id)
        findings = []
        for run in runs:
            for f in self.findings_broker.get_bulk({"run_id": run.id}):
                findings.append(FindingResponse(
                    id=str(f.id),
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    content=f.content,
                    evidence=f.evidence,
                    confidence=f.confidence,
                    run_id=str(f.run_id),
                ))
        return findings

    def get_project_reports(self, project_id: UUID, user_id: UUID = Depends(get_current_user_id)):
        """Return all reports belonging to this project."""
        project_entry = self.broker.get(project_id)
        if not project_entry: raise HTTPException(status_code=404, detail="Project not found")
        if project_entry.owner_id != user_id: raise HTTPException(status_code=404, detail="Project not found")

        reports = self.broker.list_reports(project_id)
        return [
            ReportResponse(
                id=str(r.id),
                title=r.title,
                summary=r.summary,
                content=r.content,
                report_format=r.report_format,
                project_id=str(r.project_id),
                created_at=r.created_at.isoformat(),
            )
            for r in reports
        ]


if __name__ == "__main__":
    pass
