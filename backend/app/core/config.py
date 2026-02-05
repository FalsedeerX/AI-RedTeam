from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().resolve().parent.parent.parent.parent 
ENV_FILE = PROJECT_ROOT / ".env"



class Settings(BaseSettings):
    DB_PORT: int 
    DB_HOST: str
    DB_NAME: str
    DB_SCHEMA: str
    DB_OWNER_USER: str
    DB_OWNER_PASSWORD: str
    DB_RUNTIME_USER: str
    DB_RUNTIME_PASSWORD: str
    DB_MIGRATE_USER: str
    DB_MIGRATE_PASSWORD: str

    @property
    def DB_OWNER_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_OWNER_USER}:{self.DB_OWNER_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_RUNTIME_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_RUNTIME_USER}:{self.DB_RUNTIME_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_MIGRATE_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_MIGRATE_USER}:{self.DB_MIGRATE_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        ) 


    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()



if __name__ == "__main__":
    pass

