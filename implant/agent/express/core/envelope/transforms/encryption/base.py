from typing import Any
from abc import ABC, abstractmethod


class EncryptionAlgorithm(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def encrypt(self, plaintext: bytes) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> bytes:
        raise NotImplementedError


if __name__ == "__main__":
    pass
