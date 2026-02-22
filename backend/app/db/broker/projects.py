from uuid import UUID
from sqlalchemy import select
from collections.abc import Sequence
from app.db.session import get_session
from app.db.broker.base import BaseBroker
from app.db.models import Projects, Targets, Runs, Reports


class ProjectsBroker(BaseBroker[Projects]):
    def __init__(self):
        super().__init__(Projects)

    def list_by_owner(self, owner_id: UUID) -> Sequence[Projects]:
        """ Return a list of Projects ORM owned by the speicifed user """
        return self.get_bulk({"owner_id": owner_id})

    def list_targets(self, project_id: UUID) -> Sequence[Targets]:
        """ Return the targets ORM in list associated with a specific project id """
        with get_session() as session:
            query = select(Targets).where(Targets.project_id == project_id)
            return session.scalars(query).all()

    def list_runs(self, project_id: UUID) -> Sequence[Runs]:
        """ Return the runs ORM in list associated with a specific project id """
        with get_session() as session:
            query = select(Runs).where(Runs.project_id == project_id)
            return session.scalars(query).all()

    def list_reports(self, project_id: UUID) -> Sequence[Reports]:
        """ Return the report ORM in list associated with a specific project id """
        with get_session() as session:
            query = select(Reports).where(Reports.project_id == project_id).order_by(Reports.created_at.desc())
            return session.scalars(query).all()


if __name__ == "__main__":
    pass
