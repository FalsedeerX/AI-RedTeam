import importlib
from .registry import CompressionAlgorithm, get_compression_registry

AVAILABLE_COMPRESSIONS = {
    "lz4": "express.core.envelope.transforms.compression.lz4",
    "lzma": "express.core.envelope.transforms.compression.lzma",
    "zlib": "express.core.envelope.transforms.compression.zlib",
    "brotli": "express.core.envelope.transforms.compression.brotli"
}


def load_compressions(module_list: list[str]) -> dict[str, type[CompressionAlgorithm]]:
    for algorithm in module_list:
        module_path = AVAILABLE_COMPRESSIONS.get(algorithm)
        if not module_path: raise ValueError(f"Unknown compression: {algorithm}")
        importlib.import_module(module_path)

    return get_compression_registry()


if __name__ == "__main__":
    pass
