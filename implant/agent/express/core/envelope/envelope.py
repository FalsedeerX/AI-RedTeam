import json
from typing import Any
from dataclasses import dataclass, field, fields
from express.core.envelope.transforms.encryption import EncryptionAlgorithm
from express.core.envelope.transforms.compression import CompressionAlgorithm


class AlgorithmNotFoundError(Exception):
    pass


@dataclass
class EnvelopeRuntime:
    encryption: dict[str, type[EncryptionAlgorithm]]
    compression: dict[str, type[CompressionAlgorithm]]
    _cipher_cache: dict = field(default_factory=dict)
    _compressor_cache: dict = field(default_factory=dict)

    def _hash_config(self, config: dict[str, Any]) -> str:
        return json.dumps(config, sort_keys=True)

    def get_cipher(self, name: str, config: dict[str, Any]) -> EncryptionAlgorithm:
        key = (name, self._hash_config(config))
        if key in self._cipher_cache:
            return self._cipher_cache[key]

        # create instnace and cache
        cls = self.encryption.get(name)
        if not cls: raise AlgorithmNotFoundError(f"Algorithm {name} not found")
        instance = cls(config)
        self._cipher_cache[key] = instance
        return instance

    def get_compressor(self, name: str) -> CompressionAlgorithm:
        if name in self._compressor_cache:
           return self._compressor_cache[name]

        # create instnace and cache
        cls = self.compression.get(name)
        if not cls: raise AlgorithmNotFoundError(f"Algorithm {name} not found")
        instance = cls()
        self._compressor_cache[name] = instance
        return instance

    def list_capabilities(self) -> dict[str, Any]:
        caps: dict[str, list[str]] = {}

        for key, value in vars(self).items():
            if value is None: continue
            if isinstance(value, dict):
                caps[key] = list(value.keys())
            else:
                caps[key] = [key]

        return caps


@dataclass
class Envelope:
    version: str
    session_id: str | None
    encryption: str | None
    compression: str | None
    payload: str

    @classmethod
    def from_dict(cls, data: dict) -> Envelope:
        field_names = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered)


if __name__ == "__main__":
    pass
