from app.db.models.targets import Targets
from app.db.broker.base import BaseBroker


class TargetsBroker(BaseBroker[Targets]):
    def __init__(self):
        super().__init__(Targets)


if __name__ == "__main__":
    pass
