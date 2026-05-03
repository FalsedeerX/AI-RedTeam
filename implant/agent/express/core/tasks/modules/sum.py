from dataclasses import dataclass
from express.core.runtime import AgentContext
from express.core.tasks.registry import TaskRegistry


@dataclass
class SumInput:
    a: int
    b: int


@dataclass
class SumOuput:
    result: int


@TaskRegistry.register("sum", SumInput, "1.0")
def sum(ctx: AgentContext, data: SumInput) -> SumOuput:
    return SumOuput(result=data.a + data.b)


if __name__ == "__main__":
    pass
