import tomllib
from pathlib import Path


def load_configuration(file_path: Path):
    """ Load the TOML configuration file """
    if not file_path.exists():
        raise FileExistsError(f"Configuration file {file_path} doesn't exists !")

    with open(file_path, "rb") as file:
        config = tomllib.load(file)
    return config


if __name__ == "__main__":
    pass
