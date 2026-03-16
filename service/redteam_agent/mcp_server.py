"""
Minimal MCP server (stdio) for redteam tools. No LangGraph integration.
"""
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("redteam-tools")

ALLOWED_TARGETS = {"127.0.0.1"}


@mcp.tool
def nmap_version_scan(target: str) -> dict:
    """Run a version scan with nmap -sV -F -T4 on the given target.
    Only 127.0.0.1 is allowed.
    """
    if target not in ALLOWED_TARGETS:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Target not allowed: {target}. Only 127.0.0.1 is allowed.",
            "exit_code": -1,
        }
    try:
        result = subprocess.run(
            ["nmap", "-sV", "-F", "-T4", target],
            shell=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "nmap timed out (60s)",
            "exit_code": -1,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "nmap not found",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
        }


if __name__ == "__main__":
    mcp.run()
