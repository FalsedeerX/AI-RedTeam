"""
api.py — Agent Service HTTP interface (single-run-per-container model).

A standalone FastAPI application that exposes the RedTeam Agent over HTTP
so the Backend can invoke it as a microservice.  Each container handles
exactly one run at a time.

Endpoints
---------
POST /start   — start a new agent run (non-blocking)
GET  /status  — poll status, logs, findings, HITL state
POST /hitl    — submit operator HITL decision (approve / deny)
POST /kill    — emergency stop

The heavy LangGraph stream loop runs in a background thread.
HITL synchronisation is handled via threading.Event inside RunState.
"""

import os
import uuid
import threading
import traceback

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command

from .agent import get_agent
from .run_state import (
    RunState,
    AgentCancelledError,
    init_run,
    get_current_run,
    add_log,
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    target: str


class StartRunResponse(BaseModel):
    run_id: str


class RunStatusResponse(BaseModel):
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


class HITLRequest(BaseModel):
    approved: bool


class ActionResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# LangChain message serialisation helpers
# ---------------------------------------------------------------------------

def _serialize_message(msg) -> dict:
    """Convert a LangChain message object to a JSON-serialisable dict."""
    result = {
        "type": getattr(msg, "type", "unknown"),
        "content": getattr(msg, "content", ""),
    }
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        result["tool_calls"] = [
            {"name": tc["name"], "args": tc.get("args", {})}
            for tc in msg.tool_calls
        ]
    if isinstance(msg, ToolMessage):
        result["tool_name"] = getattr(msg, "name", None)
    return result


def _summarize_messages(values: dict) -> list[dict]:
    """Extract and serialise messages from a graph step's output values."""
    messages = values.get("messages", [])
    return [_serialize_message(m) for m in messages]


def _extract_tool_calls(values: dict) -> list[dict] | None:
    """Extract tool call info from a step's messages (for log entries)."""
    for msg in values.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            return [
                {"name": tc["name"], "args": tc.get("args", {})}
                for tc in msg.tool_calls
            ]
    return None


def _serialize_hitl_payload(payload: dict) -> dict:
    """Make the LangGraph interrupt payload JSON-safe for the API response."""
    result = {
        "risk_level": payload.get("risk_level", "HIGH"),
        "description": payload.get("prompt", "Approve this action?"),
    }
    actions = payload.get("proposed_actions", [])
    serialised_actions = []
    for item in actions:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            tc, reason = item
            serialised_actions.append({
                "tool": tc.get("name", "unknown") if isinstance(tc, dict) else str(tc),
                "args": tc.get("args", {}) if isinstance(tc, dict) else {},
                "reason": str(reason),
            })
        else:
            serialised_actions.append({"raw": str(item)})
    result["proposed_actions"] = serialised_actions
    return result


# ---------------------------------------------------------------------------
# Agent execution — runs in a background thread per run
# ---------------------------------------------------------------------------

def _build_initial_state(query: str) -> dict:
    """Construct the initial LangGraph state dict for a new run."""
    return {
        "messages": [HumanMessage(content=query)],
        "llm_calls": 0,
        "current_phase": "recon",
        "directive": "",
        "findings": [],
        "last_tool_results": [],
        "phase_history": [],
        "rag_query": "",
        "rag_reason": "",
        "rag_caller": "",
    }


def _process_step(run_state: RunState, node_name: str, values: dict) -> None:
    """Parse a single graph stream event and update RunState."""
    run_state.step_count += 1

    # Update phase
    if "current_phase" in values and values["current_phase"]:
        run_state.current_phase = values["current_phase"]
        if values["current_phase"] not in run_state.phase_history:
            run_state.phase_history.append(values["current_phase"])

    # Collect findings from analyst
    if "findings" in values and values["findings"]:
        run_state.findings.extend(values["findings"])

    # Build a human-readable summary for the log
    summary_parts = []
    for msg in values.get("messages", []):
        content = getattr(msg, "content", "")
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_names = [tc["name"] for tc in msg.tool_calls]
            summary_parts.append(f"Tool calls: {', '.join(tool_names)}")
        elif isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", "unknown")
            # Truncate very long tool outputs
            preview = content[:500] + "..." if len(content) > 500 else content
            summary_parts.append(f"[{tool_name}] {preview}")
        elif content:
            preview = content[:300] + "..." if len(content) > 300 else content
            summary_parts.append(preview)

    message = " | ".join(summary_parts) if summary_parts else f"{node_name} executed"

    add_log(
        run_state,
        node=node_name,
        message=message,
        tool_calls=_extract_tool_calls(values),
        findings=values.get("findings") or None,
        messages=_summarize_messages(values),
    )


def _execute_agent(run_state: RunState, query: str, target: str) -> None:
    """
    Run the full LangGraph agent stream loop.

    Executed in a background thread.
    Blocks on HITL via run_state.hitl_event.wait() when the graph emits __interrupt__.
    """
    try:
        agent = get_agent()
        graph = agent.app

        initial_state = _build_initial_state(query)
        config_run = {
            "configurable": {"thread_id": run_state.run_id},
            "recursion_limit": 100,
        }

        current_input = initial_state
        while True:
            interrupted = False
            for event in graph.stream(current_input, config=config_run):
                # --- Kill switch ---
                if run_state.killed:
                    add_log(run_state, "system", "Run terminated by operator.")
                    run_state.status = "killed"
                    return

                # --- HITL interrupt ---
                if "__interrupt__" in event:
                    payload = event["__interrupt__"][0].value
                    run_state.pending_hitl = _serialize_hitl_payload(payload)
                    run_state.status = "hitl_pending"
                    add_log(
                        run_state,
                        node="risk_gate_node",
                        message=f"HITL required: {run_state.pending_hitl.get('description', '')}",
                    )

                    # Block until Backend sends decision via POST /hitl
                    run_state.hitl_event.wait()
                    run_state.hitl_event.clear()

                    if run_state.killed:
                        add_log(run_state, "system", "Run terminated during HITL wait.")
                        run_state.status = "killed"
                        return

                    approved = run_state.hitl_decision
                    decision_str = "approved" if approved else "denied"
                    add_log(
                        run_state,
                        node="risk_gate_node",
                        message=f"Operator {decision_str} the action.",
                    )

                    run_state.pending_hitl = None
                    run_state.status = "running"
                    current_input = Command(resume=approved)
                    interrupted = True
                    break

                # --- Normal step ---
                for node_name, values in event.items():
                    if node_name.startswith("__"):
                        continue  # skip LangGraph internal keys
                    _process_step(run_state, node_name, values)

            if not interrupted:
                break

        # --- Run completed ---
        run_state.status = "completed"
        run_state.final_result = {
            "step_count": run_state.step_count,
            "phase_history": run_state.phase_history,
            "findings_count": len(run_state.findings),
            "findings": run_state.findings,
        }
        add_log(run_state, "system", "Agent execution completed.")

    except AgentCancelledError:
        add_log(run_state, "system", "Run terminated by operator.")
        run_state.status = "killed"

    except Exception as exc:
        run_state.status = "error"
        run_state.error_message = str(exc)
        add_log(run_state, "system", f"Agent execution failed: {exc}")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require_run() -> RunState:
    """Return the current RunState or raise 404."""
    run_state = get_current_run()
    if not run_state:
        raise HTTPException(status_code=404, detail="No run active in this container")
    return run_state


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RedTeam Agent Service",
    version="0.1.0"
)

# POST /start — start a new agent run
@app.post("/start", response_model=StartRunResponse, status_code=201)
def start_run(payload: StartRunRequest):
    """
    Start a new agent run in a background thread.
    Returns the run_id if successful.
    Returns 409 if already running.
    """
    run_id = uuid.uuid4().hex
    try:
        run_state = init_run(run_id)
    except RuntimeError:
        raise HTTPException(
            status_code=409,
            detail="A run is already active in this container",
        )

    query = f"Perform a penetration test against {payload.target}"

    thread = threading.Thread(
        target=_execute_agent,
        args=(run_state, query, payload.target),
        daemon=True,
        name=f"agent-run-{run_id[:8]}",
    )
    thread.start()

    add_log(run_state, "system", f"Agent run started. Target: {payload.target}")
    return StartRunResponse(run_id=run_id)

# GET /status — poll the current state of the agent run
@app.get("/status", response_model=RunStatusResponse)
def get_status():
    """Poll the current state of the agent run."""
    run_state = _require_run()

    return RunStatusResponse(
        run_id=run_state.run_id,
        status=run_state.status,
        current_phase=run_state.current_phase,
        step_count=run_state.step_count,
        logs=run_state.logs,
        findings=run_state.findings,
        phase_history=run_state.phase_history,
        pending_hitl=run_state.pending_hitl,
        final_result=run_state.final_result,
        error_message=run_state.error_message,
    )

# POST /hitl — submit operator HITL decision (approve / deny)
@app.post("/hitl", response_model=ActionResponse)
def submit_hitl_decision(payload: HITLRequest):
    """
    Submit operator HITL decision (approve or deny).
    Unblocks the agent thread that is waiting on hitl_event.
    """
    run_state = _require_run()
    if run_state.status != "hitl_pending":
        raise HTTPException(status_code=409, detail="No HITL decision pending")

    run_state.hitl_decision = payload.approved
    run_state.hitl_event.set()
    return ActionResponse(success=True)

# POST /kill — emergency stop
@app.post("/kill", response_model=ActionResponse)
def kill_run():
    """Emergency stop — sets the kill flag and unblocks any HITL wait."""
    run_state = _require_run()

    run_state.killed = True
    run_state.hitl_event.set()   # unblock if waiting on HITL
    return ActionResponse(success=True)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    """Run the Agent Service (for development / standalone use)."""
    host = os.getenv("AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("AGENT_PORT", "8100"))
    uvicorn.run(
        "redteam_agent.api:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
