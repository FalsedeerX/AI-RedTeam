import tomllib
from pathlib import Path


def load_configuration(file_path: str):
    """ Load the TOML configuration file """
    with open(file_path, "rb") as file:
        config = tomllib.load(file)
    return config

if __name__ == "__main__":
    pass
