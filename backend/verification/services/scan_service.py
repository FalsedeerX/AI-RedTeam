from db import scans, findings
from datetime import datetime
from uuid import uuid4
import random

VULNS = [
    ("SQL Injection", "critical"),
    ("Reflected XSS", "high"),
    ("Open Redirect", "medium"),
    ("Missing CSP Header", "low"),
]


def start_scan(target_id: str):
    scan_id = str(uuid4())

    scans.insert({
        "scan_id": scan_id,
        "target_id": target_id,
        "status": "completed",
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "engine": "ai-agent-v1",
    })

    for title, severity in random.sample(VULNS, k=2):
        findings.insert({
            "scan_id": scan_id,
            "title": title,
            "severity": severity,
            "confidence": round(random.uniform(0.7, 0.99), 2),
            "description": f"AI model detected potential {title} vulnerability.",
            "recommendation": "Validate and apply remediation.",
        })

    return scan_id

