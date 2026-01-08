"""Repository model."""
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RepositoryType(str, Enum):
    """Repository source types."""

    GIT = "git"
    DATABASE = "database"
    MAINFRAME = "mainframe"


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
    source_url = Column(String(500), nullable=True)
    connection_config = Column(JSON, nullable=True)  # Store credentials encrypted
    status = Column(SAEnum(RepositoryStatus), default=RepositoryStatus.PENDING)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    tenant_id = Column(String(100), nullable=True, index=True)  # For multi-tenancy

    def __repr__(self) -> str:
        """String representation."""
        return f"<Repository {self.name} ({self.repository_type})>"
