"""
run_state.py — In-memory state for the single agent run per container.

Each container runs at most one agent run at a time.  The state is held in
a module-level global ``_current_run`` and accessed via ``init_run()`` /
``get_current_run()`` / ``reset_run()``.

HITL synchronisation uses threading.Event because the LangGraph stream loop
runs in a plain thread (not asyncio).
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class AgentCancelledError(Exception):
    """Raised when the operator activates the kill switch."""


@dataclass
class RunState:
    """Mutable state container for the single agent run."""

    run_id: str
    status: str = "running"                # running | hitl_pending | completed | error | killed
    current_phase: str = "recon"
    step_count: int = 0
    logs: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    phase_history: list[str] = field(default_factory=list)

    # HITL fields
    pending_hitl: Optional[dict] = None    # serialised interrupt payload
    hitl_event: threading.Event = field(default_factory=threading.Event)
    hitl_decision: Optional[bool] = None

    # Kill switch
    killed: bool = False

    # Final summary set when run completes
    final_result: Optional[dict] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Module-level single-run state
# ---------------------------------------------------------------------------

_current_run: Optional[RunState] = None


def init_run(run_id: str) -> RunState:
    """Initialise the single run for this container.

    Raises ``RuntimeError`` if a run is already active (status == running
    or hitl_pending).
    """
    global _current_run
    if _current_run and _current_run.status in ("running", "hitl_pending"):
        raise RuntimeError("A run is already active in this container")
    _current_run = RunState(run_id=run_id)
    return _current_run


def get_current_run() -> Optional[RunState]:
    """Return the current RunState, or None if no run has been started."""
    return _current_run


def reset_run() -> None:
    """Clear the current run (e.g. after completion or for cleanup)."""
    global _current_run
    _current_run = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_killed() -> None:
    """Raise ``AgentCancelledError`` if the operator has activated the kill switch.

    Safe to call from anywhere (tools, nodes, stream loop) — reads the
    module-global ``_current_run`` so callers don't need a ``RunState`` reference.
    """
    run = get_current_run()
    if run and run.killed:
        raise AgentCancelledError("Run terminated by operator.")


def add_log(state: RunState, node: str, message: str, **extra) -> None:
    """Append a structured log entry to the run state."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": state.step_count,
        "node": node,
        "phase": state.current_phase,
        "message": message,
        **extra,
    }
    state.logs.append(entry)
