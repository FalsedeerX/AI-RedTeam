import importlib
from .registry import EncryptionAlgorithm, get_encryption_registry

AVAILABLE_ENCRYPTIONS = {
    "fernet": "express.core.envelope.transforms.encryption.fernet",
}


def load_encryptions(module_list: list[str]) -> dict[str, type[EncryptionAlgorithm]]:
    for algorithm in module_list:
        module_path = AVAILABLE_ENCRYPTIONS.get(algorithm)
        if not module_path: raise ValueError(f"Unknown encryption: {algorithm}")
        importlib.import_module(module_path)

    return get_encryption_registry()


if __name__ == "__main__":
    pass
