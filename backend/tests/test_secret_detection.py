"""Tests for secret detection service."""
import pytest

from app.services.secret_detection_service import (
    REDACTION_MARKER,
    SecretDetectionService,
)


class TestSecretDetectionService:
    """Test secret detection service."""

    def test_detect_aws_access_key(self):
        """Test detection of AWS access key."""
        content = """
        AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) == 1
        assert result.secrets_found[0]["type"] == "aws_access_key"
        assert result.secrets_found[0]["description"] == "AWS Access Key"

    def test_detect_generic_token(self):
        """Test detection of generic API token."""
        content = """
        api_token = "FAKE_sk_test_1234567890abcdefghijklmnopqrstuvwxyz"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1

    def test_detect_api_key(self):
        """Test detection of generic API key."""
        content = """
        api_key = "sk_test_1234567890abcdefghijklmnop"
        API_SECRET = "secret_key_1234567890abcdef"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1

    def test_detect_private_key(self):
        """Test detection of private key."""
        content = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA1234567890
        -----END RSA PRIVATE KEY-----
        """
        result = SecretDetectionService.scan_content(content, "key.pem")

        assert result.has_secrets is True
        assert len(result.secrets_found) == 1
        assert result.secrets_found[0]["type"] == "private_key"

    def test_detect_password(self):
        """Test detection of password assignment."""
        content = """
        password = "MySecretPassword123!"
        db_password = "AnotherSecretPass456"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1

    def test_detect_jwt_token(self):
        """Test detection of JWT token."""
        content = """
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        """
        result = SecretDetectionService.scan_content(content, "auth.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) == 1
        assert result.secrets_found[0]["type"] == "jwt_token"

    def test_detect_database_connection_string(self):
        """Test detection of database connection string."""
        content = """
        DATABASE_URL = "postgres://user:password123@localhost:5432/mydb"
        REDIS_URL = "redis://admin:secret@redis.example.com:6379"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1

    def test_detect_stripe_key(self):
        """Test detection of Stripe key."""
        content = """
        STRIPE_SECRET_KEY = "FAKE_sk_test_1234567890abcdefghijklmnop"
        """
        result = SecretDetectionService.scan_content(content, "payment.py")

        # May match stripe_key or generic_api_key pattern
        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1

    def test_detect_google_api_key(self):
        """Test detection of Google API key."""
        content = """
        GOOGLE_API_KEY = "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 1
        # May detect both google_api_key and generic_api_key
        secret_types = [s["type"] for s in result.secrets_found]
        assert "google_api_key" in secret_types

    def test_no_secrets_in_clean_code(self):
        """Test that clean code has no secrets detected."""
        content = """
        def check_permission(user, resource):
            if user.role == 'ADMIN':
                return True
            return False
        """
        result = SecretDetectionService.scan_content(content, "auth.py")

        assert result.has_secrets is False
        assert len(result.secrets_found) == 0

    def test_redact_aws_key(self):
        """Test redaction of AWS key."""
        content = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
        redacted, count = SecretDetectionService.redact_secrets(content)

        assert count == 1
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert REDACTION_MARKER in redacted

    def test_redact_multiple_secrets(self):
        """Test redaction of multiple secrets."""
        content = """
        AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
        GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuv"
        api_key = "sk_test_abcdefghijklmnopqrstuv"
        """
        redacted, count = SecretDetectionService.redact_secrets(content)

        assert count >= 2  # At least AWS key and api_key
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert REDACTION_MARKER in redacted

    def test_redact_preserves_non_secrets(self):
        """Test that redaction preserves non-secret code."""
        content = """
        def authorize(user):
            if user.role == 'ADMIN':
                return True
        AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
        """
        redacted, count = SecretDetectionService.redact_secrets(content)

        assert count == 1
        assert "def authorize(user):" in redacted
        assert "if user.role == 'ADMIN':" in redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted

    def test_validate_no_secrets_passes_for_clean_prompt(self):
        """Test validation passes for clean prompt."""
        prompt = """
        Analyze this code:
        def check_permission(user):
            return user.is_admin
        """
        # Should not raise
        result = SecretDetectionService.validate_no_secrets_in_prompt(
            prompt, "test.py"
        )
        assert result is True

    def test_validate_no_secrets_fails_for_leaky_prompt(self):
        """Test validation fails for prompt with secrets."""
        prompt = """
        Analyze this code:
        AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
        """
        # Should raise ValueError
        with pytest.raises(ValueError, match="Security violation"):
            SecretDetectionService.validate_no_secrets_in_prompt(prompt, "test.py")

    def test_line_number_accuracy(self):
        """Test that line numbers are accurate."""
        content = """line 1
line 2
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
line 4
"""
        result = SecretDetectionService.scan_content(content, "test.py")

        assert result.has_secrets is True
        assert result.secrets_found[0]["line"] == 3

    def test_multiple_secrets_same_file(self):
        """Test detection of multiple secrets in same file."""
        content = """
        # Line 2
        AWS_KEY = "AKIAIOSFODNN7EXAMPLE"  # Line 3
        # Line 4
        GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuv"  # Line 5
        # Line 6
        password = "SuperSecret123!"  # Line 7
        """
        result = SecretDetectionService.scan_content(content, "config.py")

        assert result.has_secrets is True
        assert len(result.secrets_found) >= 2  # At least AWS key and password

    def test_secret_preview_truncation(self):
        """Test that secret preview is truncated."""
        long_secret = "a" * 100
        content = f'api_key = "{long_secret}"'
        result = SecretDetectionService.scan_content(content, "test.py")

        if result.has_secrets:
            preview = result.secrets_found[0]["preview"]
            assert len(preview) <= 23  # 20 chars + "..."
            assert preview.endswith("...")
