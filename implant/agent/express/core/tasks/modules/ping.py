from dataclasses import dataclass
from express.core.runtime import AgentContext
from express.core.tasks.registry import TaskRegistry


@dataclass
class PingInput:
    pass


@dataclass
class PingOuput:
    status: str


@TaskRegistry.register("ping", PingInput, "1.0")
def ping(ctx: AgentContext, data: PingInput) -> PingOuput:
    return PingOuput(status="pong")


if __name__ == "__main__":
    pass
