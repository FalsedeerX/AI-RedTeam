from typing import Callable
from express.core.runtime import AgentContext
from express.core.protocol.messages import BaseMessage


class Dispatcher:
    _handlers: dict[str, Callable[[AgentContext, BaseMessage], BaseMessage]] = {}

    @classmethod
    def register_hanlder(cls, op: str):
        def decorator(func: Callable):
            # duplicate guard
            if op in cls._handlers.keys():
                raise ValueError(f"Handler for {op} has already been registered")

            cls._handlers[op] = func
            return func

        return decorator


if __name__ == "__main__":
    pass
