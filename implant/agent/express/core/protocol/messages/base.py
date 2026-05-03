from dataclasses import dataclass, field


@dataclass
class BaseMessage:
    op: str = field(init=False)


if __name__ == "__main__":
    pass
