from uuid import UUID
from app.db.models.users import Users
from app.db.broker.base import BaseBroker


class UsersBroker(BaseBroker[Users]):
    def __init__(self):
        super().__init__(Users)

    def get_user_by_email(self, email: str) -> Users | None:
        """ Get user entry by specific email """
        return self.get_one({"email": email})

    def get_credential_by_email(self, email: str) -> tuple[UUID, str] | None:
        """ Ger hashed password associated with specified email """
        user_entry = self.get(email)
        if not user_entry: return None
        return user_entry.id, user_entry.hashed_password


if __name__ == "__main__":
    pass
