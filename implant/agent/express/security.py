import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class FernetCipher:
    """PBKDF2 + Fernet (AES + HMAC) wrapper"""

    def __init__(self, passphrase: str, salt: bytes = b""):
        kdf = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=390000)
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._fernet.decrypt(ciphertext)


if __name__ == "__main__":
    salt = "\\x90\\x89\\x88"
    salt_bytes = bytes.fromhex(salt.replace("\\x", ""))
    passphrase = "Top secret key"
    message = "Can you read me ?"

    cipher = FernetCipher(passphrase, salt_bytes)
    ciphertext = cipher.encrypt(message.encode())
    print(ciphertext)
