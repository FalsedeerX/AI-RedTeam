from db.models.users import Users
from db.broker.base import BaseBroker


class UsersBroker(BaseBroker[Users]):
    def __init__(self):
        super().__init__(Users)

    def get_by_email(self, email: str) -> Users | None:
        """ Get user entry by specific email """
        results = self.get_bulk({"email": email})
        return results[0] if results else None


if __name__ == "__main__":
    pass
