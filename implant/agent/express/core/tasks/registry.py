from dataclasses import dataclass
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Type, TypeVar, Generic

if TYPE_CHECKING:
    from express.core.runtime import AgentContext


T = TypeVar("T")


@dataclass
class TaskSpec(Generic[T]):
    version: str
    func: Callable[["AgentContext", T], object]
    input_model: Type[T]


class TaskRegistry:
    _tasks: dict[str, dict[str, TaskSpec]] = defaultdict(dict)

    @classmethod
    def register(cls, name: str, input_model: Type[T], version: str):
        def decorator(func: Callable[["AgentContext", T], object]):
            if version in cls._tasks[name]:
                raise ValueError(f"Task {name} (v{version}) already registered")

            cls._tasks[name][version] = TaskSpec(
                version=version,
                func=func,
                input_model=input_model,
            )
            return func

        return decorator

    @classmethod
    def list_capabilities(cls) -> dict[str, list[str]]:
        caps: defaultdict[str, list[str]] = defaultdict(list)
        for task, versions in cls._tasks.items():
            caps[task].extend(versions.keys())

        return caps

    @classmethod
    def get(cls, name: str, version: str) -> TaskSpec:
        if name not in cls._tasks:
            raise ValueError(f"Task {name} not found")
        return cls._tasks[name][version]


if __name__ == "__main__":
    pass
