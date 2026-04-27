from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from express.core.runtime import AgentContext


class TaskNotFoundError(Exception):
    pass


class TaskValidationError(Exception):
    pass


class TaskRunner:
    def __init__(self, ctx: "AgentContext"):
        self._ctx = ctx

    def execute(self, name: str, payload: dict[str, Any]):
        spec = self._ctx.task_registry.get(name, "1.0")
        if not spec: raise TaskNotFoundError(f"Task {name} is not registered")

        try:
            params = spec.input_model(**payload)
        except TypeError as ex:
            raise ValueError(f"Invalid input model for task {name}: {ex}")

        return spec.func(self._ctx, params)


if __name__ == "__main__":
    pass
