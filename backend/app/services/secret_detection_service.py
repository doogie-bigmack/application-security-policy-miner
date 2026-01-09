"""Secret detection service to prevent credentials from being sent to LLM."""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Secret patterns to detect
SECRET_PATTERNS = {
    "aws_access_key": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "description": "AWS Access Key",
    },
    "aws_secret_key": {
        "pattern": r"aws_secret_access_key\s*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        "description": "AWS Secret Access Key",
    },
    "github_token": {
        "pattern": r"ghp_[A-Za-z0-9_]{36}",
        "description": "GitHub Personal Access Token",
    },
    "github_oauth": {
        "pattern": r"gho_[A-Za-z0-9]{36}",
        "description": "GitHub OAuth Token",
    },
    "github_app": {
        "pattern": r"(ghu|ghs)_[A-Za-z0-9]{36}",
        "description": "GitHub App Token",
    },
    "slack_token": {
        "pattern": r"xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[A-Za-z0-9]{24,32}",
        "description": "Slack Token",
    },
    "slack_webhook": {
        "pattern": r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{24,}",
        "description": "Slack Webhook URL",
    },
    "generic_api_key": {
        "pattern": r"(?i)(api[_-]?key|apikey|api[_-]?secret|access[_-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
        "description": "Generic API Key",
    },
    "private_key": {
        "pattern": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "description": "Private Key",
    },
    "password_assignment": {
        "pattern": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]",
        "description": "Password Assignment",
    },
    "jwt_token": {
        "pattern": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "description": "JWT Token",
    },
    "database_connection": {
        "pattern": r"(?i)(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@[^/]+",
        "description": "Database Connection String",
    },
    "stripe_key": {
        "pattern": r"sk_live_[A-Za-z0-9]{24,}",
        "description": "Stripe Live Secret Key",
    },
    "google_api_key": {
        "pattern": r"AIza[0-9A-Za-z_-]{35}",
        "description": "Google API Key",
    },
    "azure_storage_key": {
        "pattern": r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88}",
        "description": "Azure Storage Connection String",
    },
}

# Redaction marker
REDACTION_MARKER = "[REDACTED_SECRET]"


class SecretDetectionResult:
    """Result of secret detection scan."""

    def __init__(self):
        """Initialize result."""
        self.secrets_found: list[dict[str, Any]] = []
        self.has_secrets = False

    def add_secret(
        self, secret_type: str, description: str, line_number: int, matched_text: str
    ):
        """Add a detected secret.

        Args:
            secret_type: Type of secret detected
            description: Human-readable description
            line_number: Line number where secret was found
            matched_text: The matched secret text
        """
        self.secrets_found.append({
            "type": secret_type,
            "description": description,
            "line": line_number,
            "preview": matched_text[:20] + "..." if len(matched_text) > 20 else matched_text,
        })
        self.has_secrets = True


class SecretDetectionService:
    """Service for detecting secrets in code before sending to LLM."""

    @staticmethod
    def scan_content(content: str, file_path: str) -> SecretDetectionResult:
        """Scan content for secrets.

        Args:
            content: File content to scan
            file_path: Path to file being scanned

        Returns:
            SecretDetectionResult with detected secrets
        """
        result = SecretDetectionResult()

        for secret_type, config in SECRET_PATTERNS.items():
            pattern = config["pattern"]
            description = config["description"]

            for match in re.finditer(pattern, content):
                # Get line number
                line_num = content[:match.start()].count("\n") + 1
                matched_text = match.group(0)

                result.add_secret(secret_type, description, line_num, matched_text)

                logger.warning(
                    f"Secret detected in {file_path}:{line_num}",
                    extra={
                        "file_path": file_path,
                        "line": line_num,
                        "secret_type": secret_type,
                        "description": description,
                    },
                )

        if result.has_secrets:
            logger.info(
                f"Secret scan complete for {file_path}: {len(result.secrets_found)} secrets detected"
            )
        else:
            logger.debug(f"Secret scan complete for {file_path}: no secrets found")

        return result

    @staticmethod
    def redact_secrets(content: str) -> tuple[str, int]:
        """Redact all detected secrets from content.

        Args:
            content: File content to redact

        Returns:
            Tuple of (redacted_content, secrets_count)
        """
        redacted_content = content
        secrets_count = 0

        for secret_type, config in SECRET_PATTERNS.items():
            pattern = config["pattern"]

            # Count matches before redaction
            matches = list(re.finditer(pattern, redacted_content))
            secrets_count += len(matches)

            # Redact all matches
            redacted_content = re.sub(pattern, REDACTION_MARKER, redacted_content)

        return redacted_content, secrets_count

    @staticmethod
    def validate_no_secrets_in_prompt(prompt: str, file_path: str) -> bool:
        """Validate that no secrets exist in the prompt being sent to LLM.

        Args:
            prompt: Prompt to validate
            file_path: File path for logging

        Returns:
            True if no secrets found, False if secrets detected

        Raises:
            ValueError: If secrets are found in the prompt
        """
        result = SecretDetectionService.scan_content(prompt, file_path)

        if result.has_secrets:
            logger.error(
                f"SECURITY VIOLATION: Secrets detected in prompt for {file_path}",
                extra={
                    "file_path": file_path,
                    "secrets_count": len(result.secrets_found),
                    "secret_types": [s["type"] for s in result.secrets_found],
                },
            )
            raise ValueError(
                f"Security violation: {len(result.secrets_found)} secrets detected in LLM prompt. "
                "This indicates a bug in secret redaction."
            )

        return True
