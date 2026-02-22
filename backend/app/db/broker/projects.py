from uuid import UUID
from app.db.models.projects import Projects
from app.db.broker.base import BaseBroker


class ProjectsBroker(BaseBroker[Projects]):
    def __init__(self):
        super().__init__(Projects)

    def list_by_onwer(self, owner_id: UUID) -> list[Projects]:
        """ Return a list of Projects ORM owned by the speicifed user """
        pass

    def get_detail(self, project_id: UUID)


if __name__ == "__main__":
    pass
