from uuid import UUID
from typing import Any
from dataclasses import dataclass, field
from express.core.protocol.registry import register
from .base import BaseMessage


@dataclass
@register(op="SESSION_REQ")
class SessionRequestMessage(BaseMessage):
    op: str = field(init=False, default="SESSION_REQ")
    agent_version: str
    protocol_capabilities: dict[str, list[str]]
    task_capabilities: dict[str, list[str]]
    extensions: dict[str, Any]


@dataclass
@register(op="SESSION_INIT")
class SessionInitMessage(BaseMessage):
    op: str = field(init=False, default="SESSION_INIT")
    session_id: UUID
    encryption: str | None
    compression: str | None
    config: dict[str, Any]


if __name__ == "__main__":
    pass
