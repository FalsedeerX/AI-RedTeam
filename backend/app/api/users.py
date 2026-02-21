from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from app.schema.users import UserCreate, UserAuth, UserInfo
from app.core.security import hash_password
from app.db.broker.users import UsersBroker
from app.db.session import get_session
from app.db.models.users import Users


router = APIRouter(prefix="/users", tags=["users"])


class UsersRouter:
    def __init__(self):
        self.router = router
        self.broker = UsersBroker()
        self.router.post("/register", response_model=UserInfo)(self.register)
        self.router.post("/auth", response_model=UserInfo)(self.authenticate)
        self.router.get("/profile", response_model=UserInfo)(self.get_profile)
        self.router.patch("/profile", response_model=UserInfo)(self.update_profile)

    def register(self, payload: UserCreate):
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
        user_creds = self.broker.get_credential_by_email(payload.email)
        if not user_creds: raise HTTPException(status_code=401, detail="Account doens't exists")

        # if account exists check if hashed password match
        user_id, user_passwd = user_creds
        if user_passwd != hash_password(payload.password.get_secret_value()): 
            raise HTTPException(status_code=401, detail="Incorrect login credentials") 
        return self.broker.get_user_by_email(payload.email)

    def get_profile(self):
        pass

    def update_profile(self):
        pass
