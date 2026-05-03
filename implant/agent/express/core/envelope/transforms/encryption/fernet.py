import base64
from typing import Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .registry import register_encryption
from .base import EncryptionAlgorithm


@register_encryption("fernet")
class FernetCipher(EncryptionAlgorithm):
    """ PBKDF2 + Fernet (AES + HMAC) wrapper """
    def __init__(self, config: dict[str, Any]):
        passphrase = config["passphrase"]
        salt = bytes.fromhex(config["salt"])
        kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._fernet.decrypt(ciphertext)


if __name__ == "__main__":
    pass
