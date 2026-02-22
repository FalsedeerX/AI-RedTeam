from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from app.schema.users import UserCreate, UserAuth, UserInfo, UserIdentity
from app.api.deps import get_current_user_id
from app.core.security import hash_password
from app.db.broker.users import UsersBroker
from app.db.models.users import Users


router = APIRouter(prefix="/users", tags=["users"])


class UsersRouter:
    def __init__(self):
        self.router = router
        self.broker = UsersBroker()
        self.router.post("/register", response_model=UserInfo)(self.register)
        self.router.post("/auth", response_model=UserIdentity)(self.authenticate)
        self.router.get("/me", response_model=UserInfo)(self.get_profile)
        self.router.patch("/profile", response_model=UserInfo)(self.update_profile)

    def register(self, payload: UserCreate):
        """ Registering a new user in the database """
        exists = self.broker.get_user_by_email(payload.email)
        if exists: raise HTTPException(status_code=409, detail="Email already registered")
        user_info = {
            "email": payload.email,
            "hashed_password": hash_password(payload.password.get_secret_value())
        }

        # register in database
        user_entry = self.broker.create(user_info)
        return user_entry

    def authenticate(self, payload: UserAuth):
        """
        For user login, the returning user UUID will need to be injected in the frontend as "X-User-Id".
        Need to add real session token based solution to replace this in the future.
        """
        user_creds = self.broker.get_credential_by_email(payload.email)
        if not user_creds: raise HTTPException(status_code=401, detail="Account doens't exists")

        # if account exists check if hashed password match
        user_id, user_passwd = user_creds
        if user_passwd != hash_password(payload.password.get_secret_value()):
            raise HTTPException(status_code=401, detail="Incorrect login credentials")
        return UserIdentity(user_id=user_id)

    def get_profile(self, user_id: UUID = Depends(get_current_user_id)):
        """ Peal down the session token and derive the user ORM based on its information """
        user_entry = self.broker.get(user_id)
        if not user_entry: raise HTTPException(status_code=401, detail="Not logged in")
        return user_entry

    def update_profile(self):
        """ User self-updating profile information (email/password) """
        pass
