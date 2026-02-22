from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, SecretStr, Field, ConfigDict


class UserCreate(BaseModel):
    """ Request for user account registration """
    email: EmailStr
    password: SecretStr = Field(min_length=8)


class UserAuth(BaseModel):
    """ Request for user authentication """
    email: EmailStr
    password: SecretStr = Field(min_length=8)


class UserIdentity(BaseModel):
    """
    Response for user authentication for identification,
    need to be replaced by the actual session token in future
    """
    user_id: UUID


class UserUpdate(BaseModel):
    """ Request for user self updating properties of their account """
    email: EmailStr | None = None
    password: SecretStr | None = Field(default=None, min_length=8)


class UserAdminUpdate(BaseModel):
    """ Request for admin (not implement) making a user account as verified """
    is_verified: bool | None = None


class UserInfo(BaseModel):
    """ User identity projection """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_verified: bool
    created_at: datetime


if __name__ == "__main__":
    pass
