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
    LLM_PROVIDER: str = "aws_bedrock"  # Options: aws_bedrock, azure_openai
    ANTHROPIC_API_KEY: str = ""  # Legacy - only used for direct Anthropic (not recommended)

    # AWS Bedrock Configuration
    AWS_BEDROCK_REGION: str = "us-east-1"
    AWS_BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "claude-sonnet-4"
    AZURE_OPENAI_API_VERSION: str = "2024-10-01-preview"

    # Scanning
    BATCH_SIZE: int = 50
    MAX_FILE_SIZE_MB: int = 10

    # Encryption
    # In production, use a secure key from KMS/Vault
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = "J2mtpOQ4ilLflT91hDBdAe9AT9Tw4ugn9k_3xYxtb30="


settings = Settings()
