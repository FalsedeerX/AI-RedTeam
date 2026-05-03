from typing import TypeVar, Type, Callable

from express.core.protocol.messages import BaseMessage

MESSAGE_REGISTRY: dict[str, type[BaseMessage]] = {}

T = TypeVar("T", bound=BaseMessage)


def get_message_registry() -> dict[str, type[BaseMessage]]:
    return MESSAGE_REGISTRY


def register(op: str) -> Callable[[Type[T]], Type[T]]:
    def decorator(cls: Type[T]) -> Type[T]:
        # type and duplicate guard
        if not issubclass(cls, BaseMessage):
            raise TypeError(f"{cls.__name__} must inherit BaseMessage")

        if op in MESSAGE_REGISTRY:
            raise ValueError(f"opcode {op} DTO already registered")

        # register
        MESSAGE_REGISTRY[op] = cls
        return cls

    return decorator


if __name__ == "__main__":
    pass
