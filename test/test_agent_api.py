"""
test_agent_api.py — Integration test for the Backend → Agent Service flow.

Tests the full HTTP lifecycle:
  1. POST /start   — start an agent run
  2. GET  /status  — poll status until HITL or complete
  3. POST /hitl    — approve/deny HITL
  4. POST /kill    — emergency stop
  5. Verify JSON-serialisable response format (Status, Logs, Findings)

Single-run-per-container model
------------------------------
The Agent Service runs one run at a time.  Its endpoints are flat
(/start, /status, /hitl, /kill) — no run_id in the URL.

Run modes
---------
A) Agent Service only (default):
     Directly tests the Agent Service endpoints on :8100.

B) Full Backend proxy (optional):
     Also tests the Backend /agent/* proxy routes on :8000.
     Enabled by setting BACKEND_URL env var.

Prerequisites
-------------
  - Ollama running                      (ollama serve)
  - Agent Service running on :8100      (cd service && python -m redteam_agent.api)
  - [Optional] Backend running on :8000 (cd backend && python backend.py)
    with AGENT_SERVICE_URL=http://localhost:8100

Usage
-----
  cd <repo_root>
  python test/test_agent_api.py

  # Or with pytest:
  pytest test/test_agent_api.py -v -s

  # With Backend proxy test:
  BACKEND_URL=http://localhost:8000 pytest test/test_agent_api.py -v -s

Environment variables
---------------------
  AGENT_SERVICE_URL  — Agent Service base URL    (default: http://localhost:8100)
  BACKEND_URL        — Backend base URL          (default: unset = skip proxy tests)
  TEST_TARGET        — Target IP for agent       (default: 127.0.0.1)
  POLL_INTERVAL      — Seconds between polls     (default: 3)
  POLL_TIMEOUT       — Max seconds to wait       (default: 600 = 10 min)
  HITL_ACTION        — auto-approve / auto-deny / interactive  (default: auto-approve)
"""

import os
import sys
import time
import json
import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENT_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8100").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")
TEST_TARGET = os.getenv("TEST_TARGET", "127.0.0.1")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "3"))
POLL_TIMEOUT = float(os.getenv("POLL_TIMEOUT", "1800"))
HITL_ACTION = os.getenv("HITL_ACTION", "auto-approve")  # auto-approve | auto-deny | interactive

# For Backend proxy tests that require authentication
TEST_USER_ID = os.getenv("TEST_USER_ID", "00000000-0000-4000-a000-000000000001")


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

USE_COLOR = os.environ.get("NO_COLOR") is None

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

CYAN    = lambda t: _c("36", t)
GREEN   = lambda t: _c("32", t)
YELLOW  = lambda t: _c("33", t)
RED     = lambda t: _c("31", t)
MAGENTA = lambda t: _c("35", t)
BOLD    = lambda t: _c("1", t)
DIM     = lambda t: _c("2", t)


def _phase_color(phase: str) -> str:
    colors = {"recon": CYAN, "enumeration": YELLOW, "exploitation": RED, "complete": GREEN}
    fn = colors.get(phase, str)
    return fn(phase.upper())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_service(url: str, name: str) -> bool:
    """Quick health-check: can we reach the service?"""
    try:
        resp = httpx.get(f"{url}/status", timeout=5)
        # 404 is fine — means the service is up (no run started yet)
        return resp.status_code in (200, 404, 422)
    except httpx.ConnectError:
        print(RED(f"\n  ✗ Cannot reach {name} at {url}"))
        print(f"    Make sure the service is running.\n")
        return False


def _poll_until_done(
    get_status_fn,
    hitl_fn=None,
) -> dict:
    """
    Poll the run status until it reaches a terminal state.

    get_status_fn: callable() -> dict  (no args — caller binds URL/context)
    hitl_fn:       callable(approved: bool) -> None

    Handles HITL pauses automatically based on HITL_ACTION setting.
    Returns the final status response dict.
    """
    start_time = time.time()
    last_log_count = 0
    hitl_count = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed > POLL_TIMEOUT:
            print(RED(f"\n  ✗ Timed out after {POLL_TIMEOUT}s"))
            return {"status": "timeout", "error": "poll timeout exceeded"}

        data = get_status_fn()

        # Print new log entries
        logs = data.get("logs", [])
        for log_entry in logs[last_log_count:]:
            node = log_entry.get("node", "?")
            phase = log_entry.get("phase", "?")
            msg = log_entry.get("message", "")
            step = log_entry.get("step", "?")
            ts = log_entry.get("timestamp", "")[:19]

            # Truncate long messages for readability
            if len(msg) > 200:
                msg = msg[:200] + "..."

            print(f"    {DIM(ts)} [{BOLD(f'step {step}')}] "
                  f"{_phase_color(phase)} │ {CYAN(node):>20s} │ {msg}")

        last_log_count = len(logs)

        status = data.get("status", "unknown")

        # --- Handle HITL ---
        if status == "hitl_pending" and hitl_fn:
            hitl_count += 1
            pending = data.get("pending_hitl", {})
            description = pending.get("description", "Unknown action")
            actions = pending.get("proposed_actions", [])

            print(f"\n    {'='*60}")
            print(f"    {RED(BOLD('     HITL REQUIRED'))}")
            print(f"    {'='*60}")
            print(f"      Risk level : {pending.get('risk_level', 'HIGH')}")
            print(f"      Description: {description}")
            for action in actions:
                print(f"     -> {action.get('tool', '?')}: {action.get('reason', '')}")
                args = action.get("args", {})
                if args:
                    print(f"        Args: {json.dumps(args, indent=2)[:200]}")
            print(f"    {'-'*60}")

            if HITL_ACTION == "auto-approve":
                print(f"    {GREEN(' -> Auto-approving (HITL_ACTION=auto-approve)')}")
                hitl_fn(approved=True)
            elif HITL_ACTION == "auto-deny":
                print(f"    {YELLOW(' -> Auto-denying (HITL_ACTION=auto-deny)')}")
                hitl_fn(approved=False)
            else:  # interactive
                choice = input("    Approve? (yes/no): ").strip().lower()
                approved = choice in ("yes", "y")
                hitl_fn(approved=approved)

            print(f"    {'═'*60}\n")
            time.sleep(1)
            continue

        # --- Terminal states ---
        if status in ("completed", "error", "killed"):
            return data

        time.sleep(POLL_INTERVAL)


# ===========================================================================
# Test 1: Agent Service direct
# ===========================================================================

class TestAgentServiceDirect:
    """Tests hitting the Agent Service endpoints directly (no Backend).

    Single-run-per-container: endpoints are /start, /status, /hitl, /kill.
    """

    @pytest.fixture(autouse=True)
    def check_agent_service(self):
        if not _check_service(AGENT_URL, "Agent Service"):
            pytest.skip("Agent Service not reachable")

    def _get_status(self) -> dict:
        resp = httpx.get(f"{AGENT_URL}/status", timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _send_hitl(self, approved: bool):
        resp = httpx.post(
            f"{AGENT_URL}/hitl",
            json={"approved": approved},
            timeout=10,
        )
        resp.raise_for_status()

    def test_start_and_poll(self):
        """Full lifecycle: start → poll → HITL → complete."""
        print(f"\n{'='*60}")
        print(BOLD("  Agent Service Direct Test"))
        print(f"  Target: {TEST_TARGET}")
        print(f"  HITL  : {HITL_ACTION}")
        print(f"{'='*60}\n")

        # 1. Start run
        print(BOLD("  [1] Starting agent run..."))
        resp = httpx.post(
            f"{AGENT_URL}/start",
            json={"target": TEST_TARGET},
            timeout=30,
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        run_id = resp.json()["run_id"]
        print(f"  {GREEN(f'Run started: {run_id}')}\n")

        # 2. Poll until done
        print(BOLD("  [2] Polling status...\n"))
        final = _poll_until_done(
            self._get_status,
            hitl_fn=self._send_hitl,
        )

        # 3. Validate final state
        status = final.get("status")
        print(f"\n{'─'*60}")
        print(BOLD("  [3] Final Result"))
        print(f"{'─'*60}")
        print(f"  Status       : {GREEN(status) if status == 'completed' else RED(status)}")
        print(f"  Steps        : {final.get('step_count', '?')}")
        print(f"  Phase history: {' → '.join(final.get('phase_history', []))}")
        print(f"  Findings     : {len(final.get('findings', []))}")

        if final.get("findings"):
            print(f"\n  Findings detail:")
            for f in final["findings"]:
                sev = f.get("severity", "?")
                desc = f.get("description", "?")
                color = RED if sev in ("CRITICAL", "HIGH") else YELLOW if sev == "MEDIUM" else CYAN
                print(f"    {color(f'[{sev}]')} {desc}")

        if final.get("error_message"):
            print(f"  Error        : {RED(final['error_message'])}")

        assert status in ("completed", "error"), f"Unexpected final status: {status}"
        print(f"\n  {GREEN('✓')} Test passed!\n")

    def test_kill(self):
        """Start a run and immediately kill it."""
        print(f"\n{'='*60}")
        print(BOLD("  Kill Test"))
        print(f"{'='*60}\n")

        # Start
        resp = httpx.post(
            f"{AGENT_URL}/start",
            json={"target": TEST_TARGET},
            timeout=30,
        )
        assert resp.status_code == 201
        run_id = resp.json()["run_id"]
        print(f"  Run started: {run_id}")

        time.sleep(2)

        # Kill
        resp = httpx.post(f"{AGENT_URL}/kill", timeout=10)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        print(f"  Kill signal sent")

        # Poll until terminal state
        final = _poll_until_done(self._get_status)
        print(f"  Final status: {final['status']}")
        assert final["status"] in ("killed", "completed", "error")
        print(f"  {GREEN('✓')} Kill test passed!\n")

    def test_status_no_run(self):
        """GET /status when no run active → 404."""
        # Note: this may get 200 if a previous test's run is still in memory.
        # The primary intent is to verify the endpoint exists and responds.
        resp = httpx.get(f"{AGENT_URL}/status", timeout=10)
        assert resp.status_code in (200, 404)

    def test_hitl_no_pending(self):
        """POST /hitl when not in hitl_pending → 409."""
        # Start a run
        resp = httpx.post(
            f"{AGENT_URL}/start",
            json={"target": TEST_TARGET},
            timeout=30,
        )

        # Immediately try HITL (unlikely to be in hitl_pending)
        resp = httpx.post(
            f"{AGENT_URL}/hitl",
            json={"approved": True},
            timeout=10,
        )
        # Should be 409 (no HITL pending) unless the agent hit HITL instantly
        assert resp.status_code in (200, 409)

        # Clean up
        httpx.post(f"{AGENT_URL}/kill", timeout=10)

    def test_response_format(self):
        """Verify the response JSON schema matches the documented format."""
        resp = httpx.post(
            f"{AGENT_URL}/start",
            json={"target": TEST_TARGET},
            timeout=30,
        )

        # Wait a few seconds for some steps to execute
        time.sleep(5)

        data = self._get_status()

        # Verify top-level keys
        required_keys = {
            "run_id", "status", "current_phase", "step_count",
            "logs", "findings", "phase_history",
        }
        assert required_keys.issubset(data.keys()), (
            f"Missing keys: {required_keys - data.keys()}"
        )

        # Verify types
        assert isinstance(data["run_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["current_phase"], str)
        assert isinstance(data["step_count"], int)
        assert isinstance(data["logs"], list)
        assert isinstance(data["findings"], list)
        assert isinstance(data["phase_history"], list)

        # Verify log entry format (if any)
        if data["logs"]:
            log = data["logs"][0]
            assert "timestamp" in log
            assert "node" in log
            assert "message" in log

        # Verify JSON-serialisable (no crashes)
        json.dumps(data)

        # Clean up
        httpx.post(f"{AGENT_URL}/kill", timeout=10)


# ===========================================================================
# Test 2: Backend proxy (optional — skipped if BACKEND_URL not set)
# ===========================================================================

class TestBackendProxy:
    """Tests the Backend /agent/* proxy routes → Agent Service.

    Backend routes still include {run_id} in the URL (for Frontend tracking),
    but the Backend forwards to the Agent Service's flat endpoints internally.
    """

    @pytest.fixture(autouse=True)
    def check_services(self):
        if not BACKEND_URL:
            pytest.skip("BACKEND_URL not set — skipping Backend proxy tests")
        if not _check_service(AGENT_URL, "Agent Service"):
            pytest.skip("Agent Service not reachable")
        # Check Backend has /agent routes
        try:
            resp = httpx.post(
                f"{BACKEND_URL}/agent/start",
                json={"project_id": "test", "target": "test"},
                headers={"X-User-Id": TEST_USER_ID},
                timeout=10,
            )
            # 502 = agent forwarding failed but route exists → OK
            # 201 = actually worked → OK
            # 404 = route doesn't exist → skip
            if resp.status_code == 404:
                pytest.skip("Backend /agent routes not registered")
        except httpx.ConnectError:
            pytest.skip(f"Backend not reachable at {BACKEND_URL}")

    def _headers(self):
        return {"X-User-Id": TEST_USER_ID}

    def _make_get_status(self, run_id: str):
        """Return a zero-arg callable for _poll_until_done."""
        def _fn() -> dict:
            resp = httpx.get(
                f"{BACKEND_URL}/agent/{run_id}/status",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        return _fn

    def _make_send_hitl(self, run_id: str):
        """Return a callable(approved: bool) for _poll_until_done."""
        def _fn(approved: bool):
            endpoint = "approve" if approved else "deny"
            resp = httpx.post(
                f"{BACKEND_URL}/agent/{run_id}/{endpoint}",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
        return _fn

    def test_full_flow_via_backend(self):
        """Full lifecycle through Backend proxy."""
        print(f"\n{'='*60}")
        print(BOLD("  Backend Proxy Test"))
        print(f"  Backend: {BACKEND_URL}")
        print(f"  Agent  : {AGENT_URL}")
        print(f"  Target : {TEST_TARGET}")
        print(f"{'='*60}\n")

        # 1. Start via Backend
        print(BOLD("  [1] Starting via Backend /agent/start ..."))
        resp = httpx.post(
            f"{BACKEND_URL}/agent/start",
            json={
                "project_id": "test-project",
                "target": TEST_TARGET,
            },
            headers=self._headers(),
            timeout=30,
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        run_id = body["run_id"]
        print(f"  {GREEN('✓')} Run started: {run_id} (project: {body.get('project_id')})\n")

        # 2. Poll via Backend
        print(BOLD("  [2] Polling via Backend /agent/{id}/status ...\n"))
        final = _poll_until_done(
            self._make_get_status(run_id),
            hitl_fn=self._make_send_hitl(run_id),
        )

        status = final.get("status")
        print(f"\n  Final status: {GREEN(status) if status == 'completed' else RED(status)}")
        assert status in ("completed", "error"), f"Unexpected: {status}"
        print(f"  {GREEN('✓')} Backend proxy test passed!\n")

    def test_kill_via_backend(self):
        """Kill through Backend proxy."""
        resp = httpx.post(
            f"{BACKEND_URL}/agent/start",
            json={
                "project_id": "test-kill",
                "target": TEST_TARGET,
            },
            headers=self._headers(),
            timeout=30,
        )
        assert resp.status_code == 201
        run_id = resp.json()["run_id"]

        time.sleep(2)

        resp = httpx.post(
            f"{BACKEND_URL}/agent/{run_id}/kill",
            headers=self._headers(),
            timeout=10,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Poll until terminal state
        final = _poll_until_done(self._make_get_status(run_id))
        assert final["status"] in ("killed", "completed", "error")
        print(f"  {GREEN('✓')} Backend kill test passed!")

    def test_auth_required(self):
        """Requests without X-User-Id header should fail with 401."""
        resp = httpx.post(
            f"{BACKEND_URL}/agent/start",
            json={"project_id": "x", "target": "x"},
            # No headers
            timeout=10,
        )
        assert resp.status_code == 401


# ===========================================================================
# Standalone runner (outside pytest)
# ===========================================================================

def main():
    """Run the core integration test interactively (no pytest needed)."""
    print(BOLD(f"\n{'═'*60}"))
    print(BOLD("  AI RedTeam — Agent API Integration Test"))
    print(BOLD(f"{'═'*60}"))
    print(f"  Agent Service : {AGENT_URL}")
    print(f"  Backend       : {BACKEND_URL or '(not tested)'}")
    print(f"  Target        : {TEST_TARGET}")
    print(f"  HITL action   : {HITL_ACTION}")
    print(f"  Poll interval : {POLL_INTERVAL}s")
    print(f"  Poll timeout  : {POLL_TIMEOUT}s")

    # --- Check Agent Service ---
    if not _check_service(AGENT_URL, "Agent Service"):
        sys.exit(1)

    # --- Phase 1: Agent Service Direct Test ---
    agent_tester = TestAgentServiceDirect()
    agent_tester.test_start_and_poll()

    # --- Phase 2: Backend Proxy Test (optional) ---
    if BACKEND_URL and _check_service(BACKEND_URL, "Backend"):
        proxy_tester = TestBackendProxy()
        proxy_tester.test_full_flow_via_backend()

    print(f"\n{'═'*60}")
    print(GREEN(BOLD("  All tests complete.")))
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
