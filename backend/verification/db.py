from tinydb import TinyDB, Query
from datetime import datetime

db = TinyDB("data/database.json")

users = db.table("users")
targets = db.table("targets")
scans = db.table("scans")
findings = db.table("findings")
reports = db.table("reports")
audit_logs = db.table("audit_logs")
metrics = db.table("metrics")

User = Query()
Target = Query()
Scan = Query()


def seed():
    if users.all():
        return

    users.insert({
        "username": "operator",
        "password": "redteam",
        "role": "analyst",
        "created_at": datetime.utcnow().isoformat(),
    })

    targets.insert({
        "id": "tgt-001",
        "url": "https://example.com",
        "scope": "external",
        "added_at": datetime.utcnow().isoformat(),
    })

    metrics.insert({
        "total_scans": 12,
        "total_findings": 37,
        "last_scan": datetime.utcnow().isoformat(),
    })


if __name__ == "__main__":
    seed()
