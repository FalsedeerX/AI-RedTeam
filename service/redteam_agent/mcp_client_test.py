"""
MCP client test for redteam agent.
makes mcp server through stdio and calls nmap_version_scan(127.0.0.1).
"""
import asyncio
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def _server_script_path():
    """Path to mcp_server.py so it works from repo root or service/."""
    root = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root, "mcp_server.py")


async def main():
    transport = StdioTransport(
        command=sys.executable,
        args=[_server_script_path()],
    )
    client = Client(transport)
    async with client:
        result = await client.call_tool("nmap_version_scan", {"target": "127.0.0.1"})
        # Prefer .data (deserialized dict), else .structured_content or content
        envelope = getattr(result, "data", None) or getattr(
            result, "structured_content", None
        )
        if envelope is None and getattr(result, "content", None):
            for block in result.content:
                if hasattr(block, "text"):
                    print(block.text)
                    return
        print(envelope)


if __name__ == "__main__":
    asyncio.run(main())
