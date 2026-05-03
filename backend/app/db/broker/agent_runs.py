import json
import uuid
from typing import Optional

from app.db.models.agent_runs import AgentRuns
from app.db.models.reports import Reports
from app.db.broker.base import BaseBroker
from app.db.session import get_session
from app.domain.reports import ReportFormat


class AgentRunsBroker(BaseBroker[AgentRuns]):
    def __init__(self):
        super().__init__(AgentRuns)

    def persist_report(
        self,
        run_id: str,
        project_id: uuid.UUID,
        title: str,
        summary: str,
        findings_json: list[dict],
    ) -> Optional[uuid.UUID]:
        """Atomically create a Report and link it to the agent run.

        Uses SELECT ... FOR UPDATE to lock the agent_runs row, preventing
        concurrent polls from creating duplicate reports.

        Returns the report_id (existing or newly created), or None if the
        run_id does not exist.
        """
        with get_session() as session:
            agent_run = (
                session.query(AgentRuns)
                .with_for_update()
                .filter_by(run_id=run_id)
                .first()
            )
            if not agent_run:
                return None
            if agent_run.report_id is not None:
                return agent_run.report_id

            report = Reports(
                title=title,
                summary=summary,
                content=json.dumps(findings_json),
                report_format=ReportFormat.JSON,
                project_id=project_id,
            )
            session.add(report)
            session.flush()

            agent_run.report_id = report.id
            session.flush()
            return report.id
