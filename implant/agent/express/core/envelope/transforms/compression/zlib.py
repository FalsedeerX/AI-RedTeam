import zlib
from .base import CompressionAlgorithm
from .registry import register_compression


@register_compression("zlib")
class Zlib(CompressionAlgorithm):
    def compress(self, data: bytes):
        return zlib.compress(data)

    def decompress(self, data: bytes):
        return zlib.decompress(data)


if __name__ == "__main__":
    pass
