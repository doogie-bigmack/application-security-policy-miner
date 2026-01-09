"""
Encryption service for securing sensitive data at rest.
Uses Fernet (symmetric encryption) from cryptography library.
"""

import logging

from cryptography.fernet import Fernet

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self):
        """Initialize encryption service with key from settings."""
        # In production, this should come from a secure key management service
        # like AWS KMS, HashiCorp Vault, or Azure Key Vault
        encryption_key = settings.ENCRYPTION_KEY.encode()
        self._fernet = Fernet(encryption_key)
        logger.info("Encryption service initialized")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            encrypted_str = encrypted_bytes.decode()
            logger.debug("Successfully encrypted data")
            return encrypted_str
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            decrypted_str = decrypted_bytes.decode()
            logger.debug("Successfully decrypted data")
            return decrypted_str
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode()


# Global encryption service instance
encryption_service = EncryptionService()
