"""
scan_engine.py — background scan runner for the AI RedTeam platform.

Architecture
------------
Each active scan owns a ScanState object stored in the module-level _scan_state
dict, keyed by run_id (str).  The state is written by the background coroutine
and read by the status-polling endpoint, so both must run inside the same
uvicorn worker process (the default single-process dev setup).

AI Drop-in Point
----------------
The function `run_agent` is the ONLY place that needs to change when the real
LangChain/LangGraph agent is ready.  Replace the simulated log blocks below
with a call to the agent, forwarding `run_id`, `targets`, and `scan_type`.
The rest of the infrastructure (HITL signalling, kill switch, DB status sync)
stays the same.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.db.broker import RunsBroker, FindingsBroker, ReportsBroker
from app.domain.findings import FindingType, FindingSeverity
from app.domain.reports import ReportFormat
from app.domain.runs import RunStatus


# ---------------------------------------------------------------------------
# In-memory scan state
# ---------------------------------------------------------------------------

@dataclass
class ScanState:
    logs: list[dict] = field(default_factory=list)
    status: str = "RUNNING"          # RUNNING | NEEDS_APPROVAL | COMPLETED | TERMINATED
    pending_action: Optional[str] = None
    report_type: str = "general"
    hitl_event: asyncio.Event = field(default_factory=asyncio.Event)
    hitl_approved: Optional[bool] = None
    killed: bool = False
    findings: list[dict] = field(default_factory=list)
    report_id: Optional[str] = None


_scan_state: dict[str, ScanState] = {}
_broker = RunsBroker()


def get_state(run_id: str) -> Optional[ScanState]:
    return _scan_state.get(run_id)


def approve_hitl(run_id: str) -> bool:
    state = _scan_state.get(run_id)
    if not state:
        return False
    state.hitl_approved = True
    state.hitl_event.set()
    return True


def deny_hitl(run_id: str) -> bool:
    state = _scan_state.get(run_id)
    if not state:
        return False
    state.hitl_approved = False
    state.hitl_event.set()
    return True


def kill_scan(run_id: str) -> bool:
    state = _scan_state.get(run_id)
    if not state:
        return False
    state.killed = True
    state.hitl_event.set()   # unblock any waiting HITL coroutine
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log(state: ScanState, message: str) -> None:
    state.logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
    })


def _sync_db_status(run_id: str, status: RunStatus) -> None:
    """Persist the current RunStatus to the database (best-effort)."""
    try:
        _broker.apply(UUID(run_id), {"status": status})
    except Exception:
        pass   # DB may be unavailable in dev; don't crash the scan loop


def _persist_results(run_id: str, state: ScanState) -> None:
    """
    Write findings and a report to the DB after a scan completes (best-effort).

    Reads project_id from the existing Run row, bulk-inserts findings, then
    creates a single Report row whose JSON content is the findings list.
    Stores the new report's UUID back into state.report_id so the status
    endpoint can surface it to the frontend.
    """
    try:
        run = RunsBroker().get(UUID(run_id))
        if run is None:
            return

        findings_broker = FindingsBroker()
        for finding in state.findings:
            findings_broker.create({**finding, "run_id": UUID(run_id)})

        by_severity: dict[str, int] = {}
        for f in state.findings:
            sev = f["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

        summary_parts = [f"{count} {sev}" for sev, count in sorted(by_severity.items())]
        summary = f"Found {len(state.findings)} finding(s): {', '.join(summary_parts)}."

        report = ReportsBroker().create({
            "title": f"Security Assessment — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "summary": summary,
            "content": json.dumps(state.findings),
            "report_format": ReportFormat.JSON,
            "project_id": run.project_id,
        })

        state.report_id = str(report.id)
    except Exception:
        pass   # Never crash the scan state machine on a persistence error


# ---------------------------------------------------------------------------
# AI Drop-in Point
# ---------------------------------------------------------------------------

async def run_agent(run_id: str, targets: list[str], scan_type: str) -> None:
    """
    Execute a scan for the given targets and scan_type.

    CURRENT BEHAVIOUR: simulated scan with realistic log output and one HITL
    pause so the full UI flow can be exercised end-to-end.

    TO INTEGRATE THE REAL AI AGENT:
      1. Remove (or keep as fallback) the simulated blocks below.
      2. Instantiate the LangGraph/LangChain Agent here
      3. Log the output to _log(state,message)
      4. When the agent requests human approval, call the HITL block:
             state.status = "NEEDS_APPROVAL"
             state.pending_action = "<agent's proposed action>"
             await state.hitl_event.wait()
             state.hitl_event.clear()
             if state.killed: ...
             if state.hitl_approved: ...
      5. Set state.report_type to whatever the agent determined.
    """
    state = ScanState()
    _scan_state[run_id] = state
    _sync_db_status(run_id, RunStatus.RUNNING)

    target_str = ", ".join(targets)
    report_type = "web_app" if scan_type == "web" else "network"
    state.report_type = report_type

    try:
        # -- Phase 1: Reconnaissance --
        _log(state, f"[INFO] Initializing AI RedTeam agent for targets: {target_str}")
        await asyncio.sleep(1.5)
        if state.killed:
            raise asyncio.CancelledError

        _log(state, "[INFO] Starting passive reconnaissance...")
        await asyncio.sleep(2)
        if state.killed:
            raise asyncio.CancelledError

        _log(state, f"[SUCCESS] DNS resolution complete for {targets[0]}")
        await asyncio.sleep(1)
        _log(state, "[INFO] Enumerating open ports (passive)...")
        await asyncio.sleep(2.5)
        if state.killed:
            raise asyncio.CancelledError

        _log(state, "[SUCCESS] Port scan complete: 80/tcp open, 443/tcp open, 22/tcp open")
        await asyncio.sleep(1)

        # -- HITL Pause --
        proposed_action = (
            f"nmap -sV -p 80,443 --script vuln {targets[0]}"
            if scan_type == "web"
            else f"nmap -sV -O {targets[0]}"
        )
        state.pending_action = proposed_action
        state.status = "NEEDS_APPROVAL"
        _log(state, f"[ALERT] HITL required — proposed action: {proposed_action}")

        # Wait for operator decision (approve / deny / kill)
        await state.hitl_event.wait()
        state.hitl_event.clear()
        state.pending_action = None

        if state.killed:
            raise asyncio.CancelledError

        if state.hitl_approved:
            _log(state, "[INFO] Action approved — executing vulnerability scan...")
        else:
            _log(state, "[INFO] Action denied — skipping vulnerability scan, continuing with passive analysis...")

        state.status = "RUNNING"
        await asyncio.sleep(2)
        if state.killed:
            raise asyncio.CancelledError

        # -- Phase 2: Analysis --
        _log(state, "[INFO] Analyzing service banners and response headers...")
        await asyncio.sleep(2)
        if state.killed:
            raise asyncio.CancelledError

        _log(state, "[SUCCESS] Identified potential misconfigurations in HTTP response headers")
        await asyncio.sleep(1)
        _log(state, "[INFO] Cross-referencing findings against CVE database...")
        await asyncio.sleep(2)
        if state.killed:
            raise asyncio.CancelledError

        _log(state, "[SUCCESS] CVE analysis complete — 2 medium-severity findings logged")
        await asyncio.sleep(1)

        # -- Structured findings (replace this block when real agent is wired in) --
        state.findings = [
            {
                "finding_type": FindingType.MISCONFIGURATION,
                "severity": FindingSeverity.MEDIUM,
                "title": "Missing HTTP Security Headers",
                "content": (
                    "The server response is missing several recommended security headers: "
                    "Content-Security-Policy, X-Frame-Options, and Strict-Transport-Security. "
                    "Attackers can exploit this to conduct clickjacking or content injection attacks."
                ),
                "evidence": "HTTP/1.1 200 OK — no Content-Security-Policy, X-Frame-Options, or HSTS header present.",
                "confidence": 90,
            },
            {
                "finding_type": FindingType.VULNERABILITY,
                "severity": FindingSeverity.HIGH,
                "title": "Outdated TLS Configuration Detected",
                "content": (
                    "The server accepts TLS 1.0 and TLS 1.1 connections, which are deprecated "
                    "and contain known cryptographic weaknesses (POODLE, BEAST). "
                    "Upgrade to TLS 1.2+ and disable legacy cipher suites."
                ),
                "evidence": f"nmap --script ssl-enum-ciphers output: TLSv1.0 supported on {targets[0]}:443.",
                "confidence": 85,
            },
            {
                "finding_type": FindingType.INFORMATION,
                "severity": FindingSeverity.LOW,
                "title": "Server Version Disclosure",
                "content": (
                    "The Server response header exposes the web server name and version. "
                    "This information helps attackers identify known CVEs for the specific version. "
                    "Configure the server to suppress or genericize this header."
                ),
                "evidence": "Server: Apache/2.4.51 (Ubuntu) — version exposed in HTTP response header.",
                "confidence": 95,
            },
        ]

        _log(state, "[INFO] Generating security assessment report...")
        await asyncio.sleep(1.5)
        _persist_results(run_id, state)
        _log(state, "[SUCCESS] Scan complete. Report is ready.")

        state.status = "COMPLETED"
        _sync_db_status(run_id, RunStatus.COMPLETED)

    except asyncio.CancelledError:
        _log(state, "[ALERT] Scan terminated by operator kill switch.")
        state.status = "TERMINATED"
        state.pending_action = None
        _sync_db_status(run_id, RunStatus.FAILED)
