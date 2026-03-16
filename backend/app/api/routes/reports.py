"""
reports.py — report fetch endpoints.

Flow
----
  1. GET /reports/{report_id} — fetch a persisted report by its UUID.

Reports are created automatically by scan_engine._persist_results() when a
scan completes. The frontend receives the report_id via the scan status
endpoint and uses it to navigate to the report view.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.db.broker import ReportsBroker

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    content: str
    report_format: str
    project_id: str
    created_at: str


# ---------------------------------------------------------------------------
# Router class
# ---------------------------------------------------------------------------

class ReportsRouter:
    def __init__(self):
        self.router = router
        self.broker = ReportsBroker()
        self.router.get("/{report_id}", response_model=ReportResponse)(self.get_report)

    def get_report(
        self,
        report_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ReportResponse:
        """Fetch a persisted report by its UUID."""
        report = self.broker.get(UUID(report_id))
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")

        return ReportResponse(
            id=str(report.id),
            title=report.title,
            summary=report.summary,
            content=report.content,
            report_format=report.report_format,
            project_id=str(report.project_id),
            created_at=report.created_at.isoformat(),
        )


if __name__ == "__main__":
    pass
