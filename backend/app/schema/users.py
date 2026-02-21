from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, SecretStr, Field, ConfigDict


class UserCreate(BaseModel):
    """ User account registration request """
    email: EmailStr
    password: SecretStr = Field(min_length=8)


class UserAuth(BaseModel):
    """ User authentication request """
    email: EmailStr
    password: SecretStr = Field(min_length=8)


class UserUpdate(BaseModel):
    """ User updating properties of the account """
    email: EmailStr | None = None
    password: SecretStr | None = Field(default=None, min_length=8)


class UserAdminUpdate(BaseModel):
    """ Admin patch payload for specified user """
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
