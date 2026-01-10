"""Tests for LLM provider abstraction."""
import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_provider import (
    AWSBedrockProvider,
    AzureOpenAIProvider,
    get_llm_provider,
)


class TestAWSBedrockProvider:
    """Tests for AWS Bedrock provider."""

    @patch("app.services.llm_provider.boto3")
    def test_init_with_credentials(self, mock_boto3):
        """Test initialization with explicit AWS credentials."""
        # Mock environment
        with patch.dict(
            os.environ,
            {
                "AWS_BEDROCK_REGION": "us-west-2",
                "AWS_BEDROCK_MODEL_ID": "anthropic.claude-sonnet-4-20250514-v1:0",
                "AWS_ACCESS_KEY_ID": "test-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret",
            },
        ):
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.AWS_BEDROCK_REGION = "us-west-2"
                mock_settings.AWS_BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
                mock_settings.AWS_ACCESS_KEY_ID = "test-key"
                mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"

                AWSBedrockProvider()

                # Verify boto3 client was created with credentials
                mock_boto3.client.assert_called_once()
                call_args = mock_boto3.client.call_args
                assert call_args[0][0] == "bedrock-runtime"
                assert "aws_access_key_id" in call_args[1]
                assert "aws_secret_access_key" in call_args[1]

    @patch("app.services.llm_provider.boto3")
    def test_create_message_success(self, mock_boto3):
        """Test successful message creation."""
        # Mock Bedrock response
        mock_client = MagicMock()
        mock_response = {
            "body": MagicMock(),
        }
        mock_response["body"].read.return_value = b'{"content": [{"text": "Test response"}]}'
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AWS_BEDROCK_REGION = "us-east-1"
            mock_settings.AWS_BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
            mock_settings.AWS_ACCESS_KEY_ID = ""
            mock_settings.AWS_SECRET_ACCESS_KEY = ""

            provider = AWSBedrockProvider()
            result = provider.create_message("Test prompt", max_tokens=1000)

            assert result == "Test response"
            mock_client.invoke_model.assert_called_once()

    @patch("app.services.llm_provider.boto3")
    def test_create_message_error(self, mock_boto3):
        """Test error handling in message creation."""
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = Exception("API error")
        mock_boto3.client.return_value = mock_client

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AWS_BEDROCK_REGION = "us-east-1"
            mock_settings.AWS_BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
            mock_settings.AWS_ACCESS_KEY_ID = ""
            mock_settings.AWS_SECRET_ACCESS_KEY = ""

            provider = AWSBedrockProvider()

            with pytest.raises(Exception, match="API error"):
                provider.create_message("Test prompt")


class TestAzureOpenAIProvider:
    """Tests for Azure OpenAI provider."""

    @patch("app.services.llm_provider.AzureOpenAI")
    def test_init_success(self, mock_azure_openai):
        """Test successful initialization."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_API_VERSION = "2024-10-01-preview"
            mock_settings.AZURE_OPENAI_DEPLOYMENT_NAME = "claude-sonnet-4"

            AzureOpenAIProvider()

            # Verify AzureOpenAI client was created
            mock_azure_openai.assert_called_once()
            call_args = mock_azure_openai.call_args[1]
            assert call_args["azure_endpoint"] == "https://test.openai.azure.com"
            assert call_args["api_key"] == "test-key"
            assert call_args["api_version"] == "2024-10-01-preview"

    @patch("app.services.llm_provider.AzureOpenAI")
    def test_init_missing_credentials(self, mock_azure_openai):
        """Test initialization fails without credentials."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = ""
            mock_settings.AZURE_OPENAI_API_KEY = ""

            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
                AzureOpenAIProvider()

    @patch("app.services.llm_provider.AzureOpenAI")
    def test_create_message_success(self, mock_azure_openai):
        """Test successful message creation."""
        # Mock Azure OpenAI response
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Test response"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_azure_openai.return_value = mock_client

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_API_VERSION = "2024-10-01-preview"
            mock_settings.AZURE_OPENAI_DEPLOYMENT_NAME = "claude-sonnet-4"

            provider = AzureOpenAIProvider()
            result = provider.create_message("Test prompt", max_tokens=1000, temperature=0.5)

            assert result == "Test response"
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert call_args["model"] == "claude-sonnet-4"
            assert call_args["max_tokens"] == 1000
            assert call_args["temperature"] == 0.5

    @patch("app.services.llm_provider.AzureOpenAI")
    def test_create_message_error(self, mock_azure_openai):
        """Test error handling in message creation."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_azure_openai.return_value = mock_client

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_API_VERSION = "2024-10-01-preview"
            mock_settings.AZURE_OPENAI_DEPLOYMENT_NAME = "claude-sonnet-4"

            provider = AzureOpenAIProvider()

            with pytest.raises(Exception, match="API error"):
                provider.create_message("Test prompt")


class TestGetLLMProvider:
    """Tests for provider factory function."""

    @patch("app.services.llm_provider.boto3")
    def test_get_aws_bedrock_provider(self, mock_boto3):
        """Test getting AWS Bedrock provider."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "aws_bedrock"
            mock_settings.AWS_BEDROCK_REGION = "us-east-1"
            mock_settings.AWS_BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
            mock_settings.AWS_ACCESS_KEY_ID = ""
            mock_settings.AWS_SECRET_ACCESS_KEY = ""

            provider = get_llm_provider()

            assert isinstance(provider, AWSBedrockProvider)

    @patch("app.services.llm_provider.AzureOpenAI")
    def test_get_azure_openai_provider(self, mock_azure_openai):
        """Test getting Azure OpenAI provider."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "azure_openai"
            mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
            mock_settings.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.AZURE_OPENAI_API_VERSION = "2024-10-01-preview"
            mock_settings.AZURE_OPENAI_DEPLOYMENT_NAME = "claude-sonnet-4"

            provider = get_llm_provider()

            assert isinstance(provider, AzureOpenAIProvider)

    def test_get_unsupported_provider(self):
        """Test error for unsupported provider."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "unsupported"

            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                get_llm_provider()
