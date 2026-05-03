from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserInfo(BaseModel):
    """User identity projection returned by /users/me."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_verified: bool
    created_at: datetime


if __name__ == "__main__":
    pass
