import lz4.frame
from .base import CompressionAlgorithm
from .registry import register_compression


@register_compression("lz4")
class LZ4(CompressionAlgorithm):
    def compress(self, data: bytes) -> bytes:
        return lz4.frame.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return lz4.frame.decompress(data)


if __name__ == "__main__":
    pass
