import pytest
import json
import time


def create_registration_payload(agent_id="agent-test-01"):
    return {
        "agent_id": agent_id,
        "hostname": "test-host",
        "os": "linux",
        "timestamp": int(time.time())
    }


def create_beacon_payload(agent_id="agent-test-01"):
    return {
        "agent_id": agent_id,
        "status": "alive",
        "timestamp": int(time.time())
    }


def parse_task_response(response_json):
    return json.loads(response_json)


# -------------------------
# Registration Tests
# -------------------------

def test_registration_payload_structure():
    payload = create_registration_payload()

    assert "agent_id" in payload
    assert "hostname" in payload
    assert "os" in payload
    assert "timestamp" in payload


def test_registration_payload_serializable():
    payload = create_registration_payload()

    serialized = json.dumps(payload)

    assert isinstance(serialized, str)


# -------------------------
# Beacon / Heartbeat Tests
# -------------------------

def test_beacon_payload_structure():
    payload = create_beacon_payload()

    assert payload["status"] == "alive"
    assert "agent_id" in payload


def test_beacon_timestamp_valid():
    payload = create_beacon_payload()

    now = int(time.time())

    assert abs(payload["timestamp"] - now) < 5


# -------------------------
# Task Parsing Tests
# -------------------------

def test_task_parsing():
    task = {
        "task_id": "1234",
        "command": "whoami",
        "args": []
    }

    serialized = json.dumps(task)

    parsed = parse_task_response(serialized)

    assert parsed["command"] == "whoami"
    assert parsed["task_id"] == "1234"


# -------------------------
# Command Execution Logic
# -------------------------

def execute_task(task):
    if task["command"] == "ping":
        return "pong"

    if task["command"] == "whoami":
        return "test-user"

    return "unknown"


def test_task_execution():
    task = {"command": "ping"}

    result = execute_task(task)

    assert result == "pong"


def test_unknown_command():
    task = {"command": "invalid"}

    result = execute_task(task)

    assert result == "unknown"
