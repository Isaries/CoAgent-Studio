from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "CoAgent Studio"
    API_V1_STR: str = "/api/v1"

    # SECURITY
    SECRET_KEY: str = "changethis"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str # Required

    # DATABASE
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "coagent_db"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # ADMIN
    # ADMIN
    SUPER_ADMIN: str = "admin"
    SUPER_ADMIN_PASSWORD: str = "admin"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = {
        "case_sensitive": True,
        "env_file": [".env", "../.env"],
        "extra": "ignore"
    }

settings = Settings()
