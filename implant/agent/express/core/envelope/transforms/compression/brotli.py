import brotli
from .base import CompressionAlgorithm
from .registry import register_compression


@register_compression("brotli")
class Brotli(CompressionAlgorithm):
    def compress(self, data: bytes):
        return brotli.compress(data)

    def decompress(self, data: bytes):
        return brotli.decompress(data)


if __name__ == "__main__":
    pass
