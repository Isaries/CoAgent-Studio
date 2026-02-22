from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "CoAgent Studio"
    API_V1_STR: str = "/api/v1"

    # COOKIES
    SECURE_COOKIES: bool = False  # Default to False for easier dev access, set True in prod

    # SECURITY
    SECRET_KEY: str  # Required, must be set in .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    ENCRYPTION_KEY: str  # Required

    # DATABASE
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "coagent_db"

    # REDIS
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # NEO4J (GraphRAG)
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "coagent_neo4j"

    # QDRANT (Vector DB)
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333

    # GRAPHRAG
    GRAPHRAG_BATCH_SIZE: int = 30  # Messages per extraction batch
    GRAPHRAG_CHUNK_TOKENS: int = 600  # Max tokens per chunk
    GRAPHRAG_COMMUNITY_LEVELS: int = 2  # Leiden hierarchy depth

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # ADMIN
    # APPLICATION
    TIMEZONE: str = "Asia/Taipei"

    # ADMIN
    SUPER_ADMIN: str = "admin"
    SUPER_ADMIN_PASSWORD: str = "admin"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    model_config = {"case_sensitive": True, "env_file": [".env", "../.env"], "extra": "ignore"}


settings = Settings()
