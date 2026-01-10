"""
Custom SQLAlchemy types for encrypted columns.
"""

import json

from sqlalchemy import String, Text, TypeDecorator

from app.services.encryption_service import encryption_service


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted string columns.
    Automatically encrypts on write and decrypts on read.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database."""
        if value is None:
            return None
        return encryption_service.encrypt(value)

    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database."""
        if value is None:
            return None
        return encryption_service.decrypt(value)


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted JSON columns.
    Automatically encrypts JSON on write and decrypts on read.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Serialize to JSON and encrypt before storing in database."""
        if value is None:
            return None
        json_str = json.dumps(value)
        return encryption_service.encrypt(json_str)

    def process_result_value(self, value, dialect):
        """Decrypt and deserialize from JSON when reading from database."""
        if value is None:
            return None
        json_str = encryption_service.decrypt(value)
        return json.loads(json_str)
