from pydantic import Field
from pydantic_settings import BaseSettings


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
        env_file = ".env"


settings = Settings()



if __name__ == "__main__":
    pass

