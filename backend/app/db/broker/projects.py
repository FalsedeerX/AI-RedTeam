from app.db.models.projects import Projects
from app.db.broker.base import BaseBroker


class ProjectsBroker(BaseBroker[Projects]):
    def __init__(self):
        super().__init__(Projects)


if __name__ == "__main__":
    pass
