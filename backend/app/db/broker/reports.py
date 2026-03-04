from app.db.models.reports import Reports
from app.db.broker.base import BaseBroker


class ReportsBroker(BaseBroker[Reports]):
    def __init__(self):
        super().__init__(Reports)


if __name__ == "__main__":
    pass
