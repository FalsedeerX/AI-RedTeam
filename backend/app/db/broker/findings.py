from app.db.models.findings import Findings
from app.db.broker.base import BaseBroker


class FindingsBroker(BaseBroker[Findings]):
    def __init__(self):
        super().__init__(Findings)


if __name__ == "__main__":
    pass
