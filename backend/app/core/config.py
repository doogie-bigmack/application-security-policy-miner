"""
Application configuration using Pydantic settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://policy_miner:dev_password@localhost:5432/policy_miner"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI/LLM
    ANTHROPIC_API_KEY: str = ""
    AWS_BEDROCK_REGION: str = "us-east-1"
    AZURE_OPENAI_ENDPOINT: str = ""

    # Scanning
    BATCH_SIZE: int = 50
    MAX_FILE_SIZE_MB: int = 10


settings = Settings()
