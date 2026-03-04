from app.db.models.runs import Runs
from app.db.broker.base import BaseBroker


class RunsBroker(BaseBroker[Runs]):
    def __init__(self):
        super().__init__(Runs)


if __name__ == "__main__":
    pass
