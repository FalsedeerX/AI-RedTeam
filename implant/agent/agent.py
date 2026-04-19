from pathlib import Path
from express.core.runtime.boostrap import create_bootstrap_context, bootstrap

BASE_DIR = Path(__name__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.toml"


def main():
    # create bootstrap context
    bootstrap_ctx = create_bootstrap_context(CONFIG_PATH)
    bootstrap(bootstrap_ctx)


if __name__ == "__main__":
    main()
