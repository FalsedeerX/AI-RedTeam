"""
users.py — thin profile read endpoint.

Identity is owned by Clerk. Registration, login, and password flows live in
Clerk's hosted UI and APIs, so this router only exposes ``GET /users/me``
for the frontend to hydrate the local UUID / email after a successful sign-in.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id
from app.db.broker import UsersBroker
from app.schema.users import UserInfo


router = APIRouter(prefix="/users", tags=["users"])


class UsersRouter:
    def __init__(self):
        self.router = router
        self.broker = UsersBroker()
        self.router.get("/me", response_model=UserInfo)(self.get_profile)

    def get_profile(self, user_id: UUID = Depends(get_current_user_id)):
        """Return the DB row that backs the Clerk-authenticated caller."""
        user_entry = self.broker.get(user_id)
        if not user_entry:
            raise HTTPException(status_code=401, detail="Not logged in")
        return user_entry


if __name__ == "__main__":
    pass
