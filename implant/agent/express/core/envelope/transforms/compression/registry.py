from .base import CompressionAlgorithm

COMPRESSION_REGISTRY: dict[str, type[CompressionAlgorithm]] = {}


def get_compression_registry():
    return COMPRESSION_REGISTRY


def register_compression(name: str):
    def decorator(cls: type[CompressionAlgorithm]):
        # type and duplicate guard
        if not issubclass(cls, CompressionAlgorithm):
            raise TypeError(f"{cls.__name__} must inherit CompressionAlgorithm")
        if name in COMPRESSION_REGISTRY.keys():
            raise ValueError(f"Compression algorithm {name} already registered")

        # register
        COMPRESSION_REGISTRY[name] = cls
        return cls

    return decorator


if __name__ == "__main__":
    pass
