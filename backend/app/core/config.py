from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().resolve().parent.parent.parent.parent 
ENV_FILE = PROJECT_ROOT / ".env"



class Settings(BaseSettings):
    DB_PORT: int = Field(default=5432)
    DB_HOST: str = Field(default="localhost")
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    ALEMBIC_DB_USER: str
    ALEMBIC_DB_PASSWORD: str

    @property
    def DB_URL(self) -> str:
        return (
                f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


    @property
    def ALEMBIC_DB_URL(self) -> str:
        return (
                f"postgresql+psycopg2://{self.ALEMBIC_DB_USER}:{self.ALEMBIC_DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        ) 


    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()



if __name__ == "__main__":
    pass

