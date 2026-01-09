"""Repository model."""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.models.encrypted_types import EncryptedJSON, EncryptedString

Base = declarative_base()


class RepositoryType(str, Enum):
    """Repository source types."""

    GIT = "git"
    DATABASE = "database"
    MAINFRAME = "mainframe"


class GitProvider(str, Enum):
    """Git provider types."""

    GENERIC = "generic"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_DEVOPS = "azure_devops"


class DatabaseType(str, Enum):
    """Database types for database repositories."""

    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    MYSQL = "mysql"


class RepositoryStatus(str, Enum):
    """Repository status."""

    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    SCANNING = "scanning"


class Repository(Base):
    """Repository model for tracking code and data sources."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    repository_type = Column(SAEnum(RepositoryType), nullable=False)
    git_provider = Column(SAEnum(GitProvider), nullable=True)  # Git provider (GitHub, GitLab, etc.)
    source_url = Column(String(500), nullable=True)
    connection_config = Column(EncryptedJSON, nullable=True)  # Credentials encrypted at rest
    status = Column(SAEnum(RepositoryStatus), default=RepositoryStatus.PENDING)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    webhook_secret = Column(EncryptedString(255), nullable=True)  # Secret encrypted at rest
    webhook_enabled = Column(Integer, default=0)  # Boolean: 0=disabled, 1=enabled
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    tenant_id = Column(String(100), nullable=True, index=True)  # For multi-tenancy

    # Relationships
    scan_progresses = relationship("ScanProgress", back_populates="repository", cascade="all, delete-orphan")
    secret_logs = relationship("SecretDetectionLog", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Repository {self.name} ({self.repository_type})>"
