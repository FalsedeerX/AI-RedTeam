import lzma
from .base import CompressionAlgorithm
from .registry import register_compression


@register_compression("lzma")
class LZMA(CompressionAlgorithm):
    def compress(self, data: bytes):
        return lzma.compress(data)

    def decompress(self, data: bytes):
        return lzma.decompress(data)


if __name__ == "__main__":
    pass
