from uuid import uuid4
from db import users, audit_logs, User
from datetime import datetime

def login(username, password):
    user = users.get(User.username == username)

    if not user or user["password"] != password:
        audit_logs.insert({
            "event": "login_failed",
            "username": username,
            "time": datetime.utcnow().isoformat(),
        })
        return None

    token = str(uuid4())
    return token

