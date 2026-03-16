import json
from typing import Any
from express.security import FernetCipher


class EnvelopeError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class EncryptedEnvelope:
    PROTOCOL_VERSION = 1

    def __init__(self, cipher: FernetCipher, payload_field: str = "data"):
        self.payload_field = payload_field
        self.cipher = cipher

    def unwrap(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """ Decrypt an encrypted JSON envelope """
        payload = envelope.get(self.payload_field)
        version = envelope.get("version")

        if not version or not payload:
            raise EnvelopeError("Malformed envelope")
        if version != self.PROTOCOL_VERSION:
            raise EnvelopeError("Protocol version mismatch")

        try:
            ciphertext = payload.encode()
            plaintext = self.cipher.decrypt(ciphertext)
            return json.loads(plaintext.decode())

        except Exception as ex:
            raise EnvelopeError("Invalid encrypted payload") from ex

    def wrap(self, payload: dict[str, Any]) -> dict[str, Any]:
        """ Encrypt a payload into envelope """
        plaintext = json.dumps(payload).encode()
        ciphertext = self.cipher.encrypt(plaintext)
        return {
            "version": self.PROTOCOL_VERSION,
            self.payload_field: ciphertext.decode()
        }


if __name__ == "__main__":
    pass
