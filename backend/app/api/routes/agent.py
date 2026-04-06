"""
agent.py — Backend routes that proxy to the RedTeam Agent Service.

These endpoints are the Frontend's interface for controlling agent runs.
The Backend acts as a thin proxy: it authenticates the user, resolves the
correct Agent Service container (by project_id), and forwards the request.

Single-run-per-container model
------------------------------
The Agent Service endpoints are flat (/start, /status, /hitl, /kill) with
no run_id in the URL — the container knows its own run.  The Backend keeps
run_id in its *own* routes so the Frontend can track multiple projects.

Endpoints
---------
POST /agent/start              — start a new agent run
GET  /agent/{run_id}/status    — poll agent status / logs / findings / HITL
POST /agent/{run_id}/approve   — approve a pending HITL action
POST /agent/{run_id}/deny      — deny a pending HITL action
POST /agent/{run_id}/kill      — emergency stop
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user_id
from app.db.broker.agent_runs import AgentRunsBroker
from app.services.agent_client import agent_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AgentStartRequest(BaseModel):
    project_id: str
    target: str


class AgentStartResponse(BaseModel):
    run_id: str
    project_id: str


class AgentStatusResponse(BaseModel):
    run_id: str
    status: str
    current_phase: str
    step_count: int
    logs: list[dict]
    findings: list[dict]
    phase_history: list[str]
    pending_hitl: dict | None = None
    final_result: dict | None = None
    error_message: str | None = None
    report_id: str | None = None


class AgentActionResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# Router class
# ---------------------------------------------------------------------------

class AgentRouter:
    def __init__(self):
        self.router = router
        self._agent_runs_broker = AgentRunsBroker()
        self.router.post(
            "/start", response_model=AgentStartResponse, status_code=201
        )(self.start_run)
        self.router.get(
            "/{run_id}/status", response_model=AgentStatusResponse
        )(self.get_status)
        self.router.post(
            "/{run_id}/approve", response_model=AgentActionResponse
        )(self.approve_action)
        self.router.post(
            "/{run_id}/deny", response_model=AgentActionResponse
        )(self.deny_action)
        self.router.post(
            "/{run_id}/kill", response_model=AgentActionResponse
        )(self.kill_run)

    async def start_run(
        self,
        payload: AgentStartRequest,
        user_id: UUID = Depends(get_current_user_id),
    ) -> AgentStartResponse:
        """
        Start a new agent run by forwarding the request to the Agent Service.
        """
        try:
            result = await agent_client.start_run(
                project_id=payload.project_id,
                target=payload.target,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Agent Service unreachable: {exc}",
            )

        run_id = result["run_id"]
        self._agent_runs_broker.create({
            "run_id": run_id,
            "project_id": payload.project_id,
        })
        return AgentStartResponse(run_id=run_id, project_id=payload.project_id)

    async def get_status(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> AgentStatusResponse:
        """Poll the agent run status (proxied from Agent Service).

        When the run is completed, the validated findings from
        ``final_result.findings`` are persisted as a Report (once).
        Subsequent polls return the existing ``report_id``.
        """
        agent_run = self._agent_runs_broker.get(run_id)
        if not agent_run:
            raise HTTPException(status_code=404, detail="Run not found")
        project_id = str(agent_run.project_id)

        try:
            data = await agent_client.get_status(project_id)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Agent Service unreachable: {exc}",
            )

        report_id = self._maybe_persist_report(
            run_id=run_id,
            agent_run=agent_run,
            data=data,
        )
        if report_id is not None:
            data["report_id"] = str(report_id)

        return AgentStatusResponse(**data)

    async def approve_action(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> AgentActionResponse:
        """Approve a pending HITL action."""
        agent_run = self._agent_runs_broker.get(run_id)
        if not agent_run:
            raise HTTPException(status_code=404, detail="Run not found")
        project_id = str(agent_run.project_id)

        try:
            data = await agent_client.send_hitl_decision(project_id, approved=True)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Agent Service unreachable: {exc}",
            )

        return AgentActionResponse(success=data.get("success", False))

    async def deny_action(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> AgentActionResponse:
        """Deny a pending HITL action."""
        agent_run = self._agent_runs_broker.get(run_id)
        if not agent_run:
            raise HTTPException(status_code=404, detail="Run not found")
        project_id = str(agent_run.project_id)

        try:
            data = await agent_client.send_hitl_decision(project_id, approved=False)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Agent Service unreachable: {exc}",
            )

        return AgentActionResponse(success=data.get("success", False))

    async def kill_run(
        self,
        run_id: str,
        user_id: UUID = Depends(get_current_user_id),
    ) -> AgentActionResponse:
        """Emergency stop — terminates the agent run."""
        agent_run = self._agent_runs_broker.get(run_id)
        if not agent_run:
            raise HTTPException(status_code=404, detail="Run not found")
        project_id = str(agent_run.project_id)

        try:
            data = await agent_client.kill_run(project_id)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Agent Service unreachable: {exc}",
            )

        return AgentActionResponse(success=data.get("success", False))

    # ------------------------------------------------------------------
    # Report persistence helper
    # ------------------------------------------------------------------

    def _maybe_persist_report(self, run_id: str, agent_run, data: dict):
        """Persist validated findings as a Report when a run completes.

        Returns the report UUID if a report exists (or was just created),
        otherwise None.  Designed to be idempotent and safe under
        concurrent polling.
        """
        if agent_run.report_id is not None:
            return agent_run.report_id

        if data.get("status") != "completed":
            return None

        final_result = data.get("final_result")
        if not isinstance(final_result, dict):
            logger.warning("run %s completed but final_result is missing or not a dict", run_id)
            return None

        findings = final_result.get("findings")
        if not isinstance(findings, list):
            logger.warning("run %s completed but final_result.findings is missing or not a list", run_id)
            return None

        findings_count = len(findings)
        summary = f"Agent run completed with {findings_count} finding(s)."

        try:
            return self._agent_runs_broker.persist_report(
                run_id=run_id,
                project_id=agent_run.project_id,
                title=f"Agent Run Report — {run_id[:8]}",
                summary=summary,
                findings_json=findings,
            )
        except Exception:
            logger.exception("Failed to persist report for run %s", run_id)
            return None
