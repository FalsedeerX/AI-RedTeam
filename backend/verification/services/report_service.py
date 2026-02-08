from db import scans, findings


def generate_report(scan_id: str):
    scan = scans.get(doc_id=None, scan_id=scan_id)
    scan_findings = findings.search(lambda f: f["scan_id"] == scan_id)

    return {
        "scan_id": scan_id,
        "summary": {
            "total_findings": len(scan_findings),
            "risk_level": "high" if any(f["severity"] == "critical" for f in scan_findings) else "medium",
        },
        "findings": scan_findings,
    }

