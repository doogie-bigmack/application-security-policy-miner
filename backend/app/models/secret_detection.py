"""Secret detection audit log model."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .repository import Base


class SecretDetectionLog(Base):
    """Model for tracking detected secrets in scanned files."""

    __tablename__ = "secret_detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True)
    file_path = Column(String, nullable=False)
    secret_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    line_number = Column(Integer, nullable=False)
    preview = Column(Text, nullable=False)  # Truncated preview of matched text
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository")
    tenant = relationship("Tenant")
