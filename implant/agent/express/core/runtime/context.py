import logging
from uuid import UUID
from typing import Optional
from dataclasses import dataclass, field
from express.core.tasks.runner import TaskRunner
from express.core.tasks.registry import TaskRegistry
from express.core.envelope import EnvelopeRuntime
from .profile import AgentProfile


@dataclass(kw_only=True)
class BaseContext:
    agent_version: str
    protocol_version: str
    profile: AgentProfile
    session_id: str | None
    task_registry: type[TaskRegistry]
    envelope_runtime: EnvelopeRuntime
    encryption: Optional[str] = None
    compression: Optional[str] = None
    logger: logging.Logger = field(init=False)

    def _init_logger(self, name: str, level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)


@dataclass
class BootstrapContext(BaseContext):
    session_id: str | None = field(init=False, default=None)

    def __post_init__(self):
        self.encryption = self.profile.envelope.default_encryption
        self.compression = self.profile.envelope.default_compression
        self._init_logger("Bootstrap")


@dataclass
class AgentContext(BaseContext):
    task_runner: TaskRunner = field(init=False)
    state: dict = field(default_factory=dict)

    def __post_init__(self):
        self.task_runner = TaskRunner(self)
        self._init_logger(f"Session [{self.session_id}]")


if __name__ == "__main__":
    pass
