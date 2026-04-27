from .base import EncryptionAlgorithm

ENCRYPTION_REGISTRY: dict[str, type[EncryptionAlgorithm]] = {}


def get_encryption_registry():
    return ENCRYPTION_REGISTRY


def register_encryption(name: str):
    def decorator(cls: type[EncryptionAlgorithm]):
        # type and duplicate guard
        if not issubclass(cls, EncryptionAlgorithm):
            raise TypeError(f"{cls.__name__} must inherit EncryptionAlgorithm")
        if name in ENCRYPTION_REGISTRY.keys():
            raise ValueError(f"Encryption algorithm {name} already registered")

        # register
        ENCRYPTION_REGISTRY[name] = cls
        return cls

    return decorator


if __name__ == "__main__":
    pass
