import json
import base64
import subprocess
from pathlib import Path


# resolve project root and agent directory
ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "implant" / "agent"


def run_agent():
    result = subprocess.run(
        ["python", "agent.py"],
        cwd=AGENT_DIR,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise AssertionError(
            "Agent crashed\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
        )

    output = result.stdout.strip()

    try:
        return json.loads(output)
    except Exception as e:
        raise AssertionError(
            f"Invalid JSON output:\n{output}\nError: {e}"
        )


def test_required_fields():
    data = run_agent()

    required = ["version", "session_id", "encryption", "compression", "payload"]
    for key in required:
        assert key in data, f"Missing field: {key}"


def test_field_types():
    data = run_agent()

    assert isinstance(data["version"], str)

    assert (
        data["session_id"] is None or isinstance(data["session_id"], str)
    ), "session_id must be string or null"

    assert isinstance(data["encryption"], str)
    assert isinstance(data["compression"], str)
    assert isinstance(data["payload"], str)


def test_expected_values():
    data = run_agent()

    assert data["version"] == "0.1.0"
    assert data["encryption"] == "fernet"
    assert data["compression"] == "zlib"


def test_payload_is_base64():
    data = run_agent()

    try:
        base64.b64decode(data["payload"])
    except Exception:
        raise AssertionError("payload is not valid base64")
