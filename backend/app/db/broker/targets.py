from uuid import UUID
from sqlalchemy import select
from collections.abc import Sequence
from app.db.session import get_session
from app.db.broker.base import BaseBroker
from app.db.models import Targets, Projects


class TargetsBroker(BaseBroker[Targets]):
    def __init__(self):
        super().__init__(Targets)

    def list_by_project(self, project_id: UUID) -> Sequence[Targets]:
        """ Return a list of Targets ORM owned by the specified project """
        return self.get_bulk({"project_id": project_id})

    def get_owner_id(self, target_id: UUID) -> UUID | None:
        """ Return the owner of the project entry which owns this target """
        with get_session() as session:
            query = (
                select(Projects.owner_id)
                .join(Targets, Targets.project_id == Projects.id)
                .where(Targets.id == target_id)
            )
            return session.scalar(query)


if __name__ == "__main__":
    pass
