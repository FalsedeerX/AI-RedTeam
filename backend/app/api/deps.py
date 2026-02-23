from uuid import UUID
from fastapi import Request, HTTPException


def get_current_user_id(request: Request) -> UUID:
    """ Dependency for extracting user_id from the X-User-Id in request header """
    raw_data = request.headers.get("X-User-Id")
    if not raw_data: raise HTTPException(status_code=401, detail="Not authenticated")

    # verify whether it is a valid UUID-V4
    try: return UUID(raw_data)
    except ValueError: raise HTTPException(status_code=401, detail="Invalid session identification")


if __name__ == "__main__":
    pass
