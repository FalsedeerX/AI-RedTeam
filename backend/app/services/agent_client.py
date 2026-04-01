"""
agent_client.py — HTTP client for the RedTeam Agent Service.

The Backend uses this client to communicate with the Agent Service
microservice over HTTP.  In production each project routes to a
different Agent Service container via the naming convention
``http://agent-{project_id}:8100``.

Single-run-per-container model
------------------------------
Each container handles exactly one run.  The Agent Service endpoints
do NOT include a ``run_id`` in the URL — the container knows its own
run.  The ``run_id`` is only returned from ``POST /start`` for tracing.

Environment variables
---------------------
AGENT_SERVICE_URL   — Override URL for dev (e.g. http://localhost:8100).
                      When set, *all* requests go to this single URL
                      regardless of project_id.
AGENT_SERVICE_BASE  — Base hostname template for production.
                      Default: ``http://agent``
                      Resolved as ``{base}-{project_id}:8100``.
AGENT_SERVICE_PORT  — Port on the agent container (default 8100).
"""

import os
from typing import Optional

import httpx


_TIMEOUT = httpx.Timeout(10.0, read=300.0)  # long read timeout for slow LLM ops


class AgentClient:
    """Async HTTP client that talks to a RedTeam Agent Service instance."""

    def __init__(self):
        self._override_url: Optional[str] = os.getenv("AGENT_SERVICE_URL")
        self._base: str = os.getenv("AGENT_SERVICE_BASE", "http://agent")
        self._port: str = os.getenv("AGENT_SERVICE_PORT", "8100")

    def _get_url(self, project_id: str) -> str:
        """Resolve the Agent Service URL for a given project.

        Dev mode  : AGENT_SERVICE_URL=http://localhost:8100  (ignores project_id)
        Prod mode : http://agent-{project_id}:8100
        """
        if self._override_url:
            return self._override_url.rstrip("/")
        return f"{self._base}-{project_id}:{self._port}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_run(
        self,
        project_id: str,
        target: str,
    ) -> dict:
        """POST /start — start a new agent run.

        Returns the parsed JSON body (includes ``run_id``).
        Raises ``httpx.HTTPStatusError`` on non-2xx responses.
        """
        url = self._get_url(project_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{url}/start",
                json={"target": target},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_status(self, project_id: str) -> dict:
        """GET /status — poll agent run status."""
        url = self._get_url(project_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{url}/status")
            resp.raise_for_status()
            return resp.json()

    async def send_hitl_decision(
        self,
        project_id: str,
        approved: bool,
    ) -> dict:
        """POST /hitl — send operator HITL decision."""
        url = self._get_url(project_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{url}/hitl",
                json={"approved": approved},
            )
            resp.raise_for_status()
            return resp.json()

    async def kill_run(self, project_id: str) -> dict:
        """POST /kill — emergency stop."""
        url = self._get_url(project_id)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{url}/kill")
            resp.raise_for_status()
            return resp.json()


# Singleton instance for convenience
agent_client = AgentClient()
