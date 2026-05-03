import json
import base64
import binascii
from dataclasses import asdict
from typing import Optional, TYPE_CHECKING
from express.core.protocol.messages import BaseMessage
from express.core.protocol.registry import get_message_registry
from .envelope import Envelope, EnvelopeRuntime

if TYPE_CHECKING:
    from express.core.runtime import BaseContext


class ProtocolVersionMismatchError(Exception):
    pass


class MissingPayloadError(Exception):
    pass


class MissingOpcodeError(Exception):
    pass


class UnknownOpcodeError(Exception):
    pass


class InvalidPayloadError(Exception):
    pass


class InvalidPayloadEncodingError(Exception):
    pass


class EncryptionMismatchError(Exception):
    pass


class CompressionMismatchError(Exception):
    pass


class EnvelopPipeline:
    def __init__(self, ctx: "BaseContext"):
        self._ctx: BaseContext = ctx
        self._version: str = ctx.protocol_version
        self._session_id: str | None = ctx.session_id
        self._encryption: Optional[str] = ctx.encryption
        self._compression: Optional[str] = ctx.compression
        self._runtime: EnvelopeRuntime = ctx.envelope_runtime
        self._message_registry: dict[str, type[BaseMessage]] = get_message_registry()

    def unwrap(self, raw: bytes) -> BaseMessage:
        raw_json = json.loads(raw)
        envelope = Envelope.from_dict(raw_json)

        # version guard
        if self._version != envelope.version:
            raise ProtocolVersionMismatchError(f"Expected protocol version: {self._version}")

        # cipher guard
        if self._encryption != envelope.encryption:
            raise EncryptionMismatchError(f"Expected cipher algorithm: {self._encryption}")

        # compression guard
        if self._compression != envelope.compression:
            raise CompressionMismatchError(f"Expected compressor algorithm: {self._compression}")

        # unwrap encoded payload
        raw_payload = raw_json.get("payload")
        if not raw_payload: raise MissingPayloadError("Expected field 'payload' in envelope")
        try:
            raw_message = base64.b64decode(raw_payload, validate=True)
        except (binascii.Error, ValueError):
            raise InvalidPayloadEncodingError("Expected payload in base64 encoding")

        # decrypt if needed
        if self._encryption:
            config = self._ctx.profile.envelope.encryption[self._encryption]
            cipher = self._runtime.get_cipher(self._encryption, config)
            raw_message = cipher.decrypt(raw_message)

        # decompress if needed
        if self._compression:
            compressor = self._runtime.get_compressor(self._compression)
            raw_message = compressor.decompress(raw_message)

        # return in unified DTO
        try:
            message_json = json.loads(raw_message)
        except json.JSONDecodeError:
            raise InvalidPayloadError("Invalid JSON payload")

        op_type = message_json.get("op")
        if not op_type: raise MissingOpcodeError("Missing 'op' field in payload")
        op_cls = self._message_registry.get(op_type)
        if not op_cls: raise UnknownOpcodeError(f"Unknown opcode: {op_type}")
        return op_cls(**message_json)

    def wrap(self, message: BaseMessage) -> bytes:
        raw_payload = json.dumps(asdict(message)).encode("utf-8")

        # compress if needed
        if self._compression:
            compressor = self._runtime.get_compressor(self._compression)
            raw_payload = compressor.compress(raw_payload)

        # encrypt if needed
        if self._encryption:
            config = self._ctx.profile.envelope.encryption[self._encryption]
            cipher = self._runtime.get_cipher(self._encryption, config)
            raw_payload = cipher.encrypt(raw_payload)

        # wrap the message in an evelope
        envelope = Envelope(
            version=self._version,
            session_id=self._session_id,
            encryption=self._encryption,
            compression=self._compression,
            payload=base64.b64encode(raw_payload).decode("utf-8")
        )
        return json.dumps(asdict(envelope)).encode("utf-8")


if __name__ == "__main__":
    pass
