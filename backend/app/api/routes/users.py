from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.users import UserCreate, UserAuth, UserInfo, UserIdentity
from app.api.deps import get_current_user_id
from app.core.deployment import enforce_purdue_email
from app.core.security import hash_password, verify_password
from app.db.broker import UsersBroker


router = APIRouter(prefix="/users", tags=["users"])


class UsersRouter:
    def __init__(self):
        self.router = router
        self.broker = UsersBroker()
        self.router.post("/register", status_code=201, response_model=UserInfo)(self.register)
        self.router.post("/auth", response_model=UserIdentity)(self.authenticate)
        self.router.get("/me", response_model=UserInfo)(self.get_profile)
        self.router.patch("/profile", response_model=UserInfo)(self.update_profile)

    def register(self, payload: UserCreate):
        """ Registering a new user in the database """
        normalized_email = enforce_purdue_email(payload.email)
        exists = self.broker.get_user_by_email(normalized_email)
        if exists:
            raise HTTPException(status_code=409, detail="Error: An account with this email already exists.")
        user_info = {
            "email": normalized_email,
            "hashed_password": hash_password(payload.password.get_secret_value())
        }
        user_entry = self.broker.create(user_info)
        return user_entry

    def authenticate(self, payload: UserAuth):
        """
        For user login, the returning user UUID will need to be injected in the frontend as "X-User-Id".
        Need to add real session token based solution to replace this in the future.
        """
        normalized_email = enforce_purdue_email(payload.email)
        user_creds = self.broker.get_credential_by_email(normalized_email)
        if not user_creds:
            raise HTTPException(status_code=401, detail="Error: No account was found for this email.")

        user_id, user_passwd = user_creds
        if not verify_password(payload.password.get_secret_value(), user_passwd): #change is made so that we dont try and compare two hashes of the same password
            raise HTTPException(status_code=401, detail="Error: The password you entered is incorrect.")
        return UserIdentity(user_id=user_id)

    def get_profile(self, user_id: UUID = Depends(get_current_user_id)):
        """ Peal down the session token and derive the user ORM based on its information """
        user_entry = self.broker.get(user_id)
        if not user_entry: raise HTTPException(status_code=401, detail="Not logged in")
        return user_entry

    def update_profile(self):
        """ User self-updating profile information (email/password) """
        pass


if __name__ == "__main__":
    pass
