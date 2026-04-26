from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db.broker.base import BaseBroker
from app.db.models.users import Users
from app.db.session import get_session


class UsersBroker(BaseBroker[Users]):
    def __init__(self):
        super().__init__(Users)

    def get_user_by_email(self, email: str) -> Users | None:
        """Get user entry by specific email."""
        return self.get_one({"email": email})

    def get_by_clerk_id(self, clerk_user_id: str) -> Users | None:
        """Get user entry by Clerk subject id."""
        return self.get_one({"clerk_user_id": clerk_user_id})

    def upsert_from_clerk(self, clerk_user_id: str, email: str) -> Users:
        """Idempotently link a Clerk sub to a local users row.

        Uses Postgres ``INSERT ... ON CONFLICT`` so concurrent requests for the
        same Clerk user can never produce duplicate rows.  Email is refreshed
        on each call so Clerk remains the source of truth for profile fields.
        Returns the resulting ``Users`` row.
        """
        stmt = (
            pg_insert(Users)
            .values(email=email, clerk_user_id=clerk_user_id)
            .on_conflict_do_update(
                index_elements=["clerk_user_id"],
                set_={"email": email},
            )
            .returning(Users.id)
        )

        with get_session() as session:
            user_id = session.execute(stmt).scalar_one()
            # Re-load the full row so callers get a populated ORM instance.
            user = session.get(Users, user_id)
            assert user is not None
            session.refresh(user)
            return user


if __name__ == "__main__":
    pass
