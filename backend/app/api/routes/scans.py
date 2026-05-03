"""
scans.py — scan lifecycle endpoints.

Flow
----
  1. POST /scans/start        — create a Run in DB, kick off run_agent in the background - this will be implemented when simon is ready for agent
  2. GET  /scans/{run_id}/status — poll for logs, status, pending HITL action
  3. POST /scans/{run_id}/approve — operator approves the pending AI action
  4. POST /scans/{run_id}/deny    — operator denies the pending AI action
  5. POST /scans/{run_id}/kill    — emergency stop

The heavy lifting (simulation today, real AI later) lives entirely in
app/services/scan_engine.py — this will be the ai drop-in point. 
"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id, require_project_owner, require_run_owner
from app.db.broker import RunsBroker, FindingsBroker
from app.domain.runs import RunStatus, RunType, RunPurpose
from app.services import scan_engine

router = APIRouter(prefix="/scans", tags=["scans"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ScanStartRequest(BaseModel):
    project_id: UUID
    targets: list[str]
    scan_type: str  # "web" | "network"


class ScanStartResponse(BaseModel):
    run_id: str


class ScanStatusResponse(BaseModel):
    status: str
    logs: list[dict]
    pending_action: str | None = None
    report_type: str
    report_id: str | None = None


class ActionResponse(BaseModel):
    success: bool


class FindingResponse(BaseModel):
    id: str
    finding_type: str
    severity: str
    title: str
    content: str
    evidence: str
    confidence: int
    run_id: str


# ---------------------------------------------------------------------------
# Router class
# ---------------------------------------------------------------------------

class ScansRouter:
    def __init__(self):
        self.router = router
        self.broker = RunsBroker()
        self.findings_broker = FindingsBroker()
        self.router.post("/start", response_model=ScanStartResponse, status_code=201)(self.start_scan)
        self.router.get("/{run_id}/status", response_model=ScanStatusResponse)(self.get_status)
        self.router.get("/{run_id}/findings", response_model=list[FindingResponse])(self.get_findings)
        self.router.post("/{run_id}/approve", response_model=ActionResponse)(self.approve_action)
        self.router.post("/{run_id}/deny", response_model=ActionResponse)(self.deny_action)
        self.router.post("/{run_id}/kill", response_model=ActionResponse)(self.kill_scan)

    async def start_scan(
        self,
        payload: ScanStartRequest,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ScanStartResponse:
        """
        Create a Run record, then fire the scan agent as an asyncio background task.
        Returns the run_id so the client can poll for status.
        """
        require_project_owner(payload.project_id, user_id)
        run_type = RunType.SCAN if payload.scan_type == "network" else RunType.OSINT
        raw_command = json.dumps({
            "targets": payload.targets,
            "scan_type": payload.scan_type,
        })

        run_entry = self.broker.create({
            "project_id": payload.project_id,
            "run_type": run_type,
            "purpose": RunPurpose.PRIMARY,
            "status": RunStatus.QUEUED,
            "raw_command": raw_command,
        })

        run_id = str(run_entry.id)

        # Fire-and-forget: the coroutine manages its own state in scan_engine._scan_state.
        # Replace scan_engine.run_agent with your real AI agent call when ready.
        asyncio.create_task(scan_engine.run_agent(run_id, payload.targets, payload.scan_type))

        return ScanStartResponse(run_id=run_id)

    def get_status(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ScanStatusResponse:
        """
        Poll the current state of a running scan.
        Returns logs accumulated so far, current status, and any pending HITL action.
        """
        require_run_owner(run_id, user_id)
        state = scan_engine.get_state(run_id)
        if not state:
            # Scan may not have started yet or run_id is invalid
            raise HTTPException(status_code=404, detail="Scan not found")

        return ScanStatusResponse(
            status=state.status,
            logs=state.logs,
            pending_action=state.pending_action,
            report_type=state.report_type,
            report_id=state.report_id,
        )

    def get_findings(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> list[FindingResponse]:
        """Return all persisted findings for a completed run."""
        require_run_owner(run_id, user_id)
        rows = self.findings_broker.get_bulk({"run_id": UUID(run_id)})
        return [
            FindingResponse(
                id=str(row.id),
                finding_type=row.finding_type,
                severity=row.severity,
                title=row.title,
                content=row.content,
                evidence=row.evidence,
                confidence=row.confidence,
                run_id=str(row.run_id),
            )
            for row in rows
        ]

    def approve_action(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ActionResponse:
        """Signal the scan agent that the operator approved the pending action."""
        require_run_owner(run_id, user_id)
        success = scan_engine.approve_hitl(run_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scan not found")
        return ActionResponse(success=True)

    def deny_action(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ActionResponse:
        """Signal the scan agent that the operator denied the pending action."""
        require_run_owner(run_id, user_id)
        success = scan_engine.deny_hitl(run_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scan not found")
        return ActionResponse(success=True)

    def kill_scan(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> ActionResponse:
        """Emergency stop — terminates the scan immediately."""
        require_run_owner(run_id, user_id)
        success = scan_engine.kill_scan(run_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scan not found")
        return ActionResponse(success=True)


if __name__ == "__main__":
    pass
