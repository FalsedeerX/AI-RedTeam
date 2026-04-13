from abc import ABC, abstractmethod


class CompressionAlgorithm(ABC):
    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        raise NotImplementedError


if __name__ == "__main__":
    pass
