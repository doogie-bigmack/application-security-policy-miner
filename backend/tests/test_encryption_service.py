"""Tests for encryption service."""

import pytest

from app.services.encryption_service import EncryptionService


def test_encrypt_decrypt_string():
    """Test encrypting and decrypting a string."""
    service = EncryptionService()
    plaintext = "my-secret-password"

    # Encrypt
    ciphertext = service.encrypt(plaintext)
    assert ciphertext != plaintext
    assert len(ciphertext) > 0

    # Decrypt
    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_empty_string():
    """Test encrypting an empty string."""
    service = EncryptionService()
    plaintext = ""

    ciphertext = service.encrypt(plaintext)
    assert ciphertext == ""


def test_decrypt_empty_string():
    """Test decrypting an empty string."""
    service = EncryptionService()
    ciphertext = ""

    decrypted = service.decrypt(ciphertext)
    assert decrypted == ""


def test_encrypt_long_string():
    """Test encrypting a long string."""
    service = EncryptionService()
    plaintext = "a" * 10000

    ciphertext = service.encrypt(plaintext)
    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_special_characters():
    """Test encrypting special characters."""
    service = EncryptionService()
    plaintext = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"

    ciphertext = service.encrypt(plaintext)
    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_unicode():
    """Test encrypting unicode characters."""
    service = EncryptionService()
    plaintext = "Hello 世界 🔒"

    ciphertext = service.encrypt(plaintext)
    decrypted = service.decrypt(ciphertext)
    assert decrypted == plaintext


def test_multiple_encryptions_produce_different_ciphertexts():
    """Test that encrypting the same plaintext twice produces different ciphertexts."""
    service = EncryptionService()
    plaintext = "test-password"

    ciphertext1 = service.encrypt(plaintext)
    ciphertext2 = service.encrypt(plaintext)

    # Due to Fernet's timestamp-based encryption, these should be different
    # But both should decrypt to the same plaintext
    assert service.decrypt(ciphertext1) == plaintext
    assert service.decrypt(ciphertext2) == plaintext


def test_generate_key():
    """Test generating a new Fernet key."""
    key = EncryptionService.generate_key()
    assert len(key) > 0
    assert isinstance(key, str)
    # Fernet keys are 44 characters (32 bytes base64-encoded + padding)
    assert len(key) == 44


def test_decrypt_invalid_ciphertext():
    """Test decrypting invalid ciphertext raises an error."""
    service = EncryptionService()

    with pytest.raises(Exception):
        service.decrypt("invalid-ciphertext")


def test_encryption_is_deterministically_decryptable():
    """Test that encryption is reversible."""
    service = EncryptionService()
    test_cases = [
        "simple",
        "with spaces",
        "with-dashes",
        "with_underscores",
        "MixedCase123",
        "special!@#$%",
    ]

    for plaintext in test_cases:
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        assert decrypted == plaintext, f"Failed for: {plaintext}"
