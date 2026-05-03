import pkgutil
import importlib


def load_all_tasks():
    import express.core.tasks.modules as package

    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package.__name__}.{module.name}")


def load_tasks(modules: list[str]):
    base = "express.core.tasks.modules"

    for name in modules:
        importlib.import_module(f"{base}.{name}")


if __name__ == "__main__":
    pass
