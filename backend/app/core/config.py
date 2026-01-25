from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().resolve().parent.parent.parent.parent 
ENV_FILE = PROJECT_ROOT / ".env"



class Settings(BaseSettings):
    DB_PORT: int 
    DB_HOST: str
    DB_NAME: str
    DB_MASTER_USER: str
    DB_MASTER_PASSWORD: str
    DB_RUNTIME_USER: str
    DB_RUNTIME_PASSWORD: str
    DB_ALEMBIC_USER: str
    DB_ALEMBIC_PASSWORD: str

    @property
    def DB_MASTER_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_MASTER_USER}:{self.DB_MASTER_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_RUNTIME_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_RUNTIME_USER}:{self.DB_RUNTIME_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_ALEMBIC_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_ALEMBIC_USER}:{self.DB_ALEMBIC_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        ) 


    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()



if __name__ == "__main__":
    pass

