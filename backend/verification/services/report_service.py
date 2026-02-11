from tinydb import Query
from ..db import scans, findings

Scan = Query()


def generate_report(scan_id: str):
    scan = scans.get(Scan.scan_id == scan_id)

    if not scan:
        return {
            "error": "Scan not found",
            "scan_id": scan_id,
        }

    scan_findings = findings.search(lambda f: f["scan_id"] == scan_id)

    return {
        "scan_id": scan_id,
        "summary": {
            "total_findings": len(scan_findings),
            "risk_level": (
                "high"
                if any(f["severity"] == "critical" for f in scan_findings)
                else "medium"
            ),
        },
        "findings": scan_findings,
    }

